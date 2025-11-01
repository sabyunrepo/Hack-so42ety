export default function Settings() {

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-5 font-sans">
      {/* 메인 카드 */}
      <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg p-10">
        {/* 아이콘 */}
        <div className="flex justify-center items-center mb-4"></div>

        {/* 제목 */}
        <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
          목소리 설정
        </h1>
        <p className="text-sm text-gray-600 text-center mb-8">
          오디오 파일을 업로드하여 맞춤형 목소리를 생성합니다.
        </p>

        {/* 설정 폼 */}
        <form className="space-y-5"></form>
          {/* 이름 입력 */}
          <div className="space-y-2"></div>

          {/* 설명 입력 (선택사항) */}
          <div className="space-y-2"></div>

          {/* 오디오 파일 업로드 */}
          <div className="space-y-2"></div>

          {/* 버튼 그룹 */}
          <div className="flex gap-3 mt-6"></div>

          {/* 안내 사항 */}
      </div>
    </div>
  )
}
