import '@testing-library/jest-dom'
import { vi } from 'vitest'

// jsdom does not implement scrollIntoView, which chat components call on update.
window.HTMLElement.prototype.scrollIntoView = vi.fn()
