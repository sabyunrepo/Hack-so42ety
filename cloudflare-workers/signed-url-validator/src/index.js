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
 * @returns {Promise<Object>} - { valid: boolean, isShared?: boolean, reason?: string }
 */
async function validateSignedUrl(url, signingKey) {
  const urlObj = new URL(url);
  const verify = urlObj.searchParams.get('verify');
  const token = urlObj.searchParams.get('token');
  const shared = urlObj.searchParams.get('shared');

  // 1. 파라미터 존재 확인 (shared 포함)
  if (!verify || !token || shared === null) {
    return { valid: false, reason: 'Missing verify, token, or shared parameter' };
  }

  // 2. 만료 시간 확인
  const expiration = parseInt(verify, 10);
  const now = Math.floor(Date.now() / 1000);

  if (now > expiration) {
    return { valid: false, reason: 'URL expired' };
  }

  // 3. 서명 검증 (is_shared 포함)
  const signString = `${urlObj.pathname}-${verify}-${shared}`;
  const expectedToken = await generateSignature(signString, signingKey);

  if (token !== expectedToken) {
    return { valid: false, reason: 'Invalid token signature' };
  }

  return {
    valid: true,
    isShared: shared === '1'  // 공개 여부 반환
  };
}

/**
 * 파일 확장자로 콘텐츠 타입 추론
 * @param {string} pathname - URL 경로
 * @returns {string} - 'video' | 'audio' | 'image' | 'metadata' | 'default'
 */
function inferContentType(pathname) {
  const ext = pathname.split('.').pop()?.toLowerCase();

  const typeMap = {
    // 비디오
    'mp4': 'video',
    'webm': 'video',
    'mov': 'video',

    // 오디오
    'mp3': 'audio',
    'wav': 'audio',
    'ogg': 'audio',
    'aac': 'audio',

    // 이미지
    'png': 'image',
    'jpg': 'image',
    'jpeg': 'image',
    'gif': 'image',
    'webp': 'image',

    // 메타데이터
    'json': 'metadata',
  };

  return typeMap[ext] || 'default';
}

/**
 * R2에서 파일 가져오기 (Cache API 적용)
 * @param {R2Bucket} bucket - R2 버킷 바인딩
 * @param {string} pathname - 파일 경로 (예: /shared/books/test.mp4)
 * @param {Request} request - 원본 요청 객체
 * @param {ExecutionContext} ctx - Workers 실행 컨텍스트
 * @param {boolean} useCache - Cache API 사용 여부 (기본: true)
 * @returns {Promise<Response>} - 파일 응답 또는 404
 */
async function fetchFromR2(bucket, pathname, request, ctx, useCache = true) {
  const key = pathname.startsWith('/') ? pathname.slice(1) : pathname;
  const contentType = inferContentType(pathname);

  // Cache API 사용 (공개 콘텐츠 또는 인증된 개인 콘텐츠)
  if (useCache) {
    const cache = caches.default;

    // 정규화된 캐시 키 생성 (쿼리 파라미터 제거)
    const normalizedUrl = new URL(pathname, request.url);
    normalizedUrl.search = '';  // 쿼리 파라미터 제거

    const cacheKey = new Request(normalizedUrl.toString(), {
      method: 'GET',
      headers: request.headers
    });

    // 캐시 확인
    let response = await cache.match(cacheKey);
    if (response) {
      console.log(`[CACHE HIT] ${key} (${contentType})`);

      // HEAD 요청이면 body 제거
      if (request.method === 'HEAD') {
        return new Response(null, {
          status: response.status,
          statusText: response.statusText,
          headers: response.headers
        });
      }

      return response;
    }

    // R2 조회
    console.log(`[R2] Fetching key: ${key} (${contentType})`);
    const object = await bucket.get(key);

    if (!object) {
      console.log(`[R2] Not found: ${key}`);
      return new Response('Not Found', {
        status: 404,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' }
      });
    }

    // 응답 헤더 설정
    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set('etag', object.httpEtag);
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
    headers.set('Access-Control-Allow-Headers', 'Content-Type');
    headers.set('Cache-Control', 'public, max-age=2592000, immutable');

    response = new Response(object.body, { headers });

    // GET 요청으로만 캐시 저장 (HEAD는 캐시 불가)
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    console.log(`[CACHE MISS → STORED] ${key} (${contentType})`);

    // HEAD 요청이면 body 제거
    if (request.method === 'HEAD') {
      return new Response(null, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers
      });
    }

    return response;
  }

  // Cache API 미사용 (비공개 콘텐츠 - 브라우저 캐시만)
  console.log(`[R2] Fetching key: ${key} (${contentType})`);
  const object = await bucket.get(key);

  if (!object) {
    console.log(`[R2] Not found: ${key}`);
    return new Response('Not Found', {
      status: 404,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  }

  // 응답 헤더 설정
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('etag', object.httpEtag);
  headers.set('Access-Control-Allow-Origin', '*');
  headers.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
  headers.set('Access-Control-Allow-Headers', 'Content-Type');

  // 콘텐츠 타입별 Cache-Control (브라우저 캐시)
  const cacheConfig = {
    'video': 'private, max-age=21600',   // 6시간
    'audio': 'private, max-age=10800',   // 3시간
    'image': 'private, max-age=86400',   // 24시간
    'metadata': 'private, max-age=3600', // 1시간
    'default': 'private, max-age=3600'   // 1시간
  };
  headers.set('Cache-Control', cacheConfig[contentType]);

  console.log(`[R2] Found: ${key} (${contentType}), size: ${object.size} bytes`);

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

    // 1. 공개 콘텐츠는 즉시 R2에서 가져오기 (Cache API 적용)
    if (url.pathname.startsWith('/shared/')) {
      console.log(`[PUBLIC SHARED] ${url.pathname}`);
      return fetchFromR2(R2_BUCKET, url.pathname, request, ctx, true);
    }

    // 2. 개인 콘텐츠는 토큰 검증 후 처리
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

    // 3. 검증 성공 - Cache API 사용 (공개/비공개 모두)
    // 토큰 검증을 통과했으므로 안전하게 캐싱 가능
    const contentLabel = validation.isShared ? 'PUBLIC' : 'PRIVATE';
    console.log(`[ALLOWED - ${contentLabel} USER CONTENT] ${url.pathname}`);
    return fetchFromR2(R2_BUCKET, url.pathname, request, ctx, true);
  },
};
