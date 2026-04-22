import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AppLayout from '@/components/layout/AppLayout'
import Dashboard from '@/pages/Dashboard'
import RealEstatePage from '@/pages/RealEstatePage'
import AssetPage from '@/pages/AssetPage'
import StockPage from '@/pages/StockPage'
import PensionPage from '@/pages/PensionPage'
import RetirementPage from '@/pages/RetirementPage'
import Settings from '@/pages/Settings'

const qc = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="real-estate" element={<RealEstatePage />} />
            <Route path="stock"       element={<StockPage />} />
            <Route path="pension"     element={<PensionPage />} />
            <Route path="savings"     element={<AssetPage type="SAVINGS" />} />
            <Route path="physical"    element={<AssetPage type="PHYSICAL" />} />
            <Route path="etc"         element={<AssetPage type="ETC" />} />
            <Route path="retirement"  element={<RetirementPage />} />
            <Route path="settings"    element={<Settings />} />
            <Route path="*"           element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
