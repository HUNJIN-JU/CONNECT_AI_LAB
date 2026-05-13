import { ArrowRight } from 'lucide-react'

export default function Hero() {
  return (
    <section className="py-16 sm:py-24 px-6">
      <div className="max-w-4xl mx-auto text-center">
        <p className="text-sm font-semibold tracking-wider uppercase text-gray-500 mb-4">
          {/* TODO: 회사·브랜드 한 줄 */}
          Connect AI · 1인 기업 두뇌
        </p>
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-gray-900 mb-6">
          {/* TODO: H1은 [행동] without [고통] 또는 [숫자][결과][시간] 패턴 */}
          AI 1인 기업, <br className="hidden sm:block" />
          100% 무료로 시작
        </h1>
        <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed">
          {/* TODO: 무엇·누구·결과를 1줄에 응축 */}
          나만의 AI 직원 9명이 24시간 일하는 자동화. 클라우드 토큰 0원, 데이터는 내 컴퓨터에만.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a href="#pricing" className="inline-flex items-center justify-center gap-2 bg-gray-900 text-white px-7 py-3.5 rounded-xl font-semibold hover:bg-gray-800 transition-all shadow-lg shadow-gray-900/10">
            지금 시작하기 <ArrowRight className="w-4 h-4" />
          </a>
          <a href="#features" className="inline-flex items-center justify-center gap-2 border border-gray-300 px-7 py-3.5 rounded-xl font-semibold text-gray-900 hover:bg-gray-50 transition-all">
            기능 둘러보기
          </a>
        </div>
        <p className="mt-10 text-sm text-gray-500">
          {/* TODO: 본인 제품에 맞게 신뢰 시그널 */}
          이미 1만 명이 사용 중 · GitHub ⭐ 2.4K · 100% 오픈소스
        </p>
      </div>
    </section>
  )
}
