import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import ChatPage from './pages/ChatPage'

const App = () => {
  return (
    <div >
      <Navbar />
      <Routes>
        <Route path='/' element={<ChatPage />} />
      </Routes>
    </div>
  )
}

export default App;
