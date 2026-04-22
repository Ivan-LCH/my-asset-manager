import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Home, TrendingUp, Shield,
  PiggyBank, Gem, Music, Settings, Sunset,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/',            icon: LayoutDashboard, label: '대시보드'   },
  { to: '/real-estate', icon: Home,            label: '부동산'     },
  { to: '/stock',       icon: TrendingUp,      label: '주식'       },
  { to: '/pension',     icon: Shield,          label: '연금'       },
  { to: '/savings',     icon: PiggyBank,       label: '예적금'     },
  { to: '/physical',    icon: Gem,             label: '실물자산'   },
  { to: '/etc',         icon: Music,           label: '기타'       },
]

const PLAN_ITEMS = [
  { to: '/retirement', icon: Sunset, label: '은퇴 계획' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* 로고 */}
      <div className="px-5 py-5 border-b border-gray-800">
        <h1 className="text-base font-bold text-blue-400 tracking-tight">💼 Asset Manager</h1>
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'
              )
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}

        {/* 구분선 + 계획 메뉴 */}
        <div className="pt-3 mt-2 border-t border-gray-800">
          <p className="px-3 text-[10px] font-semibold text-gray-600 uppercase tracking-wider mb-1">계획</p>
          {PLAN_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-600/20 text-blue-400'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* 설정 */}
      <div className="px-2 py-3 border-t border-gray-800">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'bg-blue-600/20 text-blue-400'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'
            )
          }
        >
          <Settings className="w-4 h-4 flex-shrink-0" />
          설정
        </NavLink>
      </div>
    </aside>
  )
}
