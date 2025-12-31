/**
 * Cloudflare Workers - Signed URL Validator
 * 비공개 콘텐츠에 대한 Signed URL 토큰 검증
 *
 * @author Claude Code
 * @date 2025-12-31
 */

/**
 * HMAC-SHA256 서명 생성
 * @param {string} data - 서명할 데이터
 * @param {string} key - 서명 키
 * @returns {Promise<string>} - Hex 형식의 서명
 */
async function generateSignature(data, key) {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(key);
  const dataBuffer = encoder.encode(data);

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', cryptoKey, dataBuffer);
  const hashArray = Array.from(new Uint8Array(signature));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Signed URL 검증
 * @param {string} url - 검증할 URL
 * @param {string} signingKey - 서명 키
 * @returns {Promise<Object>} - { valid: boolean, reason?: string }
 */
async function validateSignedUrl(url, signingKey) {
  const urlObj = new URL(url);
  const verify = urlObj.searchParams.get('verify');
  const token = urlObj.searchParams.get('token');

  // 1. 파라미터 존재 확인
  if (!verify || !token) {
    return { valid: false, reason: 'Missing verify or token parameter' };
  }

  // 2. 만료 시간 확인
  const expiration = parseInt(verify, 10);
  const now = Math.floor(Date.now() / 1000);

  if (now > expiration) {
    return { valid: false, reason: 'URL expired' };
  }

  // 3. 서명 검증
  const signString = `${urlObj.pathname}-${verify}`;
  const expectedToken = await generateSignature(signString, signingKey);

  if (token !== expectedToken) {
    return { valid: false, reason: 'Invalid token signature' };
  }

  return { valid: true };
}

/**
 * R2에서 파일 가져오기
 * @param {R2Bucket} bucket - R2 버킷 바인딩
 * @param {string} pathname - 파일 경로 (예: /shared/books/test.mp4)
 * @returns {Promise<Response>} - 파일 응답 또는 404
 */
async function fetchFromR2(bucket, pathname) {
  // pathname: "/shared/books/test.mp4" → key: "shared/books/test.mp4"
  const key = pathname.startsWith('/') ? pathname.slice(1) : pathname;

  console.log(`[R2] Fetching key: ${key}`);

  const object = await bucket.get(key);

  if (!object) {
    console.log(`[R2] Not found: ${key}`);
    return new Response('Not Found', {
      status: 404,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  }

  // R2 객체의 메타데이터를 HTTP 헤더로 변환
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('etag', object.httpEtag);

  // CORS 헤더 추가
  headers.set('Access-Control-Allow-Origin', '*');
  headers.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Content-Type');

  // CDN 캐시 최적화 헤더 추가
  // 공개 콘텐츠는 30일, 비공개는 6시간 캐싱
  const isPublic = pathname.startsWith('/shared/');
  if (isPublic) {
    // 공개 콘텐츠: 장기 캐싱 (30일)
    headers.set('Cache-Control', 'public, max-age=2592000, immutable');
  } else {
    // 비공개 콘텐츠: 토큰 만료 시간과 동일 (6시간)
    headers.set('Cache-Control', 'private, max-age=21600');
  }

  console.log(`[R2] Found: ${key}, size: ${object.size} bytes, type: ${object.httpMetadata?.contentType || 'unknown'}`);

  return new Response(object.body, { headers });
}

/**
 * Workers 메인 핸들러
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // OPTIONS 요청 처리 (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // 환경 변수에서 Signing Key와 R2 바인딩 가져오기
    const SIGNING_KEY = env.SIGNING_KEY || 'not-used-public-mode';
    const R2_BUCKET = env.R2_BUCKET;

    // R2 바인딩 확인
    if (!R2_BUCKET) {
      console.error('[ERROR] R2_BUCKET binding not found');
      return new Response('Service temporarily unavailable', {
        status: 500,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }

    // 1. 공개 콘텐츠는 즉시 R2에서 가져오기
    if (url.pathname.startsWith('/shared/')) {
      console.log(`[PUBLIC] ${url.pathname}`);
      return fetchFromR2(R2_BUCKET, url.pathname);
    }

    // 2. 비공개 콘텐츠는 토큰 검증
    console.log(`[PRIVATE] Validating: ${url.pathname}`);
    const validation = await validateSignedUrl(url.href, SIGNING_KEY);

    if (!validation.valid) {
      console.error(`[FORBIDDEN] ${url.pathname} - ${validation.reason}`);
      return new Response(`Forbidden: ${validation.reason}`, {
        status: 403,
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'X-Error-Reason': validation.reason,
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // 3. 검증 성공 시 R2에서 가져오기
    console.log(`[ALLOWED] ${url.pathname}`);
    return fetchFromR2(R2_BUCKET, url.pathname);
  },
};
