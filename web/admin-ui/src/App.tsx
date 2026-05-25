import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ExtractionPage from './pages/ExtractionPage'
import HealthPage from './pages/HealthPage'
import RepositoriesPage from './pages/RepositoriesPage'
import LibraryDetailPage from './pages/LibraryDetailPage'

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
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route path="/library/:ecosystem/:name" element={<LibraryDetailPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
