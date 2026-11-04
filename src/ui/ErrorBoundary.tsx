/** @jsxRuntime classic */
import * as React from 'react'
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface State {
  failed: boolean
}

/** Shows a readable message instead of a blank screen when WebGL or the model cannot load. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Gallery failed to start:', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="g-fatal" role="alert">
        <h1>The gallery could not start</h1>
        <p>This screen needs WebGL. Please reload the page, or open it in an up-to-date browser.</p>
        <button type="button" className="g-btn g-btn--primary" onClick={() => window.location.reload()}>
          Reload
        </button>
      </div>
    )
  }
}
