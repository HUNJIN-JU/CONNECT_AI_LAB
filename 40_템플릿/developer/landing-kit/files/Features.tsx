import { Zap, Shield, Brain } from 'lucide-react'

const features = [
  { icon: Brain, title: '내 두뇌처럼 일함', body: 'AI가 내 지식·결정·메모를 컨텍스트로 작동. 클라우드에 안 올라감.' },
  { icon: Zap,   title: '24시간 자동 운영', body: '9명 AI 직원이 영상 분석·콘텐츠 작성·일정 관리 자동. 텔레그램 보고.' },
  { icon: Shield, title: '데이터 100% 로컬', body: '모든 처리가 내 컴퓨터에서. 외부 토큰 0원, 외부 서버에 데이터 전송 X.' },
]

export default function Features() {
  return (
    <section id="features" className="py-16 sm:py-24 px-6 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-900 mb-4">진짜로 일하는 AI 1인 기업</h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">구독료 없이 시작, 클라우드 비용 없이 운영</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((f) => {
            const Icon = f.icon
            return (
              <div key={f.title} className="text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gray-900 text-white mb-5">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-gray-600 leading-relaxed">{f.body}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
