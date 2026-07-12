import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ThemeProvider } from './context/ThemeContext';
import Header from './components/Header';

describe('Theme Switching (Phase 10)', () => {
  it('toggles theme between aero and brutalist and updates data-theme attribute', () => {
    render(
      <ThemeProvider>
        <Header wsConnected={true} />
      </ThemeProvider>
    );

    // Initial state (defaults to aero)
    expect(document.documentElement.getAttribute('data-theme')).toBe('aero');
    const toggleBtn = screen.getByRole('button', { name: /brutalist/i });
    
    // Click toggle
    fireEvent.click(toggleBtn);
    
    // Assert transition to brutalist
    expect(document.documentElement.getAttribute('data-theme')).toBe('brutalist');
    
    // Click toggle again
    const toggleBtn2 = screen.getByRole('button', { name: /aero/i });
    fireEvent.click(toggleBtn2);
    
    // Assert transition back to aero
    expect(document.documentElement.getAttribute('data-theme')).toBe('aero');
  });
});
