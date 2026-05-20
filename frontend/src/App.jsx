import { Show, SignIn, UserButton } from '@clerk/react'
import BrowsePage from './pages/BrowsePage'

export default function App() {
  return (
    <>
      <Show when="signed-out">
        <div className="min-h-screen bg-[#2B102B] flex items-center justify-center">
          <SignIn />
        </div>
      </Show>
      <Show when="signed-in">
        <BrowsePage />
      </Show>
    </>
  )
}
