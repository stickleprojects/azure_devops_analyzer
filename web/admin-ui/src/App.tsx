import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ExtractionPage from './pages/ExtractionPage'
import HealthPage from './pages/HealthPage'
import RadarPage from './pages/RadarPage'
import RadarHistoryPage from './pages/RadarHistoryPage'
import RepositoriesPage from './pages/RepositoriesPage'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/extraction" element={<ExtractionPage />} />
            <Route path="/health" element={<HealthPage />} />
            <Route path="/radar" element={<RadarPage />} />
            <Route path="/radar/history" element={<RadarHistoryPage />} />
            <Route path="/repositories" element={<RepositoriesPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
