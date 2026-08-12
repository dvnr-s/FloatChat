import React from 'react'
import MessageBox from '../components/MessageBox';

const ChatPage = () => {
    return (
        <div className='min-h-screen bg-gradient-to-br from-sky-900 via-slate-950 to-emerald-900
    flex flex-col items-center justify-center p-4 gap-2'>
            <h1 className='text-6xl sm:text-7xl font-light bg-gradient-to-r from-emerald-400 via-sky-300 to-blue-500 bg-clip-text text-transparent text-center h-22'>FloatChat</h1>
            <MessageBox />
        </div>
    )
}

export default ChatPage;