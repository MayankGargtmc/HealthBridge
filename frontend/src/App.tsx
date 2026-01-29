import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Patients from './pages/Patients'
import Diseases from './pages/Diseases'
import Documents from './pages/Documents'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<Upload />} />
        <Route path="patients" element={<Patients />} />
        <Route path="diseases" element={<Diseases />} />
        <Route path="documents" element={<Documents />} />
      </Route>
    </Routes>
  )
}

export default App
