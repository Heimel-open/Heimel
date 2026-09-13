import { Routes, Route } from 'react-router'
import { Toaster } from '@/components/ui/sonner'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import DraftPage from './pages/DraftPage'
import QueuePage from './pages/QueuePage'
import WatchlistPage from './pages/WatchlistPage'
import LearnPage from './pages/LearnPage'
import ValoLiveDemo from './pages/ValoLiveDemo'
import EnterprisePaymentDemo from './pages/EnterprisePaymentDemo'
import HealthcareScenarioPage from './pages/HealthcareScenarioPage'
import AmbassadorOnboardingPage from './pages/AmbassadorOnboardingPage'
import DeviceExecutionDemoPage from './pages/DeviceExecutionDemoPage'
import PeaceCapabilityDemo from './pages/PeaceCapabilityDemo'
import PeaceZeroGpuDemo from './pages/PeaceZeroGpuDemo'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/peace" element={<PeaceCapabilityDemo />} />
        <Route path="/peace/zerogpu" element={<PeaceZeroGpuDemo />} />
        <Route path="/healthcare-demo" element={<HealthcareScenarioPage />} />
        <Route path="/payment-mandate-demo" element={<EnterprisePaymentDemo />} />
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/app" element={<Dashboard />} />
          <Route path="/onboarding" element={<AmbassadorOnboardingPage />} />
          <Route path="/draft" element={<DraftPage />} />
          <Route path="/queue" element={<QueuePage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/demo" element={<ValoLiveDemo />} />
          <Route path="/iot-ot-boundary" element={<DeviceExecutionDemoPage />} />
        </Route>
      </Routes>
      <Toaster position="top-right" />
    </>
  )
}
