// Tests for UI components.

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Button, Badge, ProgressBar } from '../src/components';

// Simple test to verify testing setup works
describe('Testing Setup', () => {
  it('should render a simple component', () => {
    const TestComponent = () => <div>Test Component</div>;
    render(<TestComponent />);
    expect(screen.getByText('Test Component')).toBeDefined();
  });
});

describe('Button Component', () => {
  it('should render with text', () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByText('Click Me')).toBeDefined();
  });

  it('should handle click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click Me</Button>);
    fireEvent.click(screen.getByText('Click Me'));
    expect(handleClick).toHaveBeenCalled();
  });

  it('should show loading state', () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByText('Loading')).toBeDefined();
  });
});

describe('Badge Component', () => {
  it('should render with text', () => {
    render(<Badge>Test Badge</Badge>);
    expect(screen.getByText('Test Badge')).toBeDefined();
  });

  it('should apply variant class', () => {
    render(<Badge variant="critical">Critical</Badge>);
    const badge = screen.getByText('Critical');
    expect(badge.className).toContain('red');
  });
});

describe('ProgressBar Component', () => {
  it('should render with value', () => {
    render(<ProgressBar value={50} />);
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar.getAttribute('aria-valuenow')).toBe('50');
  });

  it('should show label when enabled', () => {
    render(<ProgressBar value={75} showLabel />);
    expect(screen.getByText('75/100')).toBeDefined();
  });
});