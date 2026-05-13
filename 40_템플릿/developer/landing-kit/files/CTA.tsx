import { ArrowRight } from 'lucide-react'

export default function CTA() {
  return (
    <section className="py-16 sm:py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-3xl p-10 sm:p-16 text-center text-white shadow-2xl">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">지금 1인 기업을 시작하세요</h2>
          <p className="text-lg text-gray-300 max-w-xl mx-auto mb-8">가입 1분. 다운로드 30초. 첫 AI 직원 5분 안에 일 시작.</p>
          <a href="#pricing" className="inline-flex items-center justify-center gap-2 bg-white text-gray-900 px-8 py-4 rounded-xl font-semibold hover:bg-gray-100 transition-all shadow-lg">
            무료로 시작 <ArrowRight className="w-4 h-4" />
          </a>
          <p className="mt-5 text-sm text-gray-400">신용카드 불필요 · 영구 무료 플랜 포함</p>
        </div>
      </div>
    </section>
  )
}
