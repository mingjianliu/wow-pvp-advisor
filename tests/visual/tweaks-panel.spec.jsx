import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

describe('Tweaks Components', () => {
  const TweakToggle = window.TweakToggle;
  const TweakSlider = window.TweakSlider;
  const TweaksPanel = window.TweaksPanel;

  it('renders and operates TweakToggle', () => {
    const handleChange = vi.fn();
    render(
      <TweakToggle
        label="Color by pick rate"
        value={false}
        onChange={handleChange}
      />
    );

    expect(screen.getByText('Color by pick rate')).toBeInTheDocument();
    const btn = screen.getByRole('switch');
    expect(btn).toHaveAttribute('aria-checked', 'false');

    fireEvent.click(btn);
    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('renders and operates TweakSlider', () => {
    const handleChange = vi.fn();
    render(
      <TweakSlider
        label="Font size"
        value={16}
        min={10}
        max={20}
        unit="px"
        onChange={handleChange}
      />
    );

    expect(screen.getByText('Font size')).toBeInTheDocument();
    expect(screen.getByText('16px')).toBeInTheDocument();

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '18' } });
    expect(handleChange).toHaveBeenCalledWith(18);
  });

  it('opens TweaksPanel on postMessage and closes on click dismiss', async () => {
    render(
      <TweaksPanel title="Tweaks Panel Title">
        <div>Child Content</div>
      </TweaksPanel>
    );

    // Initial state: not visible
    expect(screen.queryByText('Tweaks Panel Title')).not.toBeInTheDocument();

    // Send active message to trigger open state
    await act(async () => {
      window.dispatchEvent(
        new MessageEvent('message', {
          data: { type: '__activate_edit_mode' },
          origin: '*'
        })
      );
    });

    expect(screen.getByText('Tweaks Panel Title')).toBeInTheDocument();
    expect(screen.getByText('Child Content')).toBeInTheDocument();

    // Close the panel using the dismiss button
    const closeBtn = screen.getByRole('button', { name: /Close tweaks/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByText('Tweaks Panel Title')).not.toBeInTheDocument();
  });
});
