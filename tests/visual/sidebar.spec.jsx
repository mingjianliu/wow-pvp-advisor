import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

describe('Sidebar React Component', () => {
  const Sidebar = window.Sidebar;

  const mockCluster = {
    rank: 1,
    pct: 75.0,
    count: 15,
    canonical_code: 'mock-loadout-code-123',
    takes: [
      { id: 81022, pct: 100.0 }
    ],
    skips: [],
    flex_takes: []
  };

  const mockGroup = {
    spec: 'restoration-shaman',
    sample_size: 20,
    talents: {
      core: [{ id: 81022, name: 'Healing Stream Totem', pct: 100.0, pts: 1 }],
      flex: []
    },
    tree: {
      trees: [
        {
          id: 1,
          label: 'Class Tree',
          nodes: [
            { id: 81022, name: 'Healing Stream Totem', spellId: 10001 }
          ]
        }
      ]
    }
  };

  it('renders cluster details correctly', () => {
    const handleCopy = vi.fn();
    const handleHover = vi.fn();
    const handleLeave = vi.fn();
    const setActivePlayer = vi.fn();

    render(
      <Sidebar
        cluster={mockCluster}
        group={mockGroup}
        onCopy={() => handleCopy('mock-loadout-code-123')}
        heatmap={false}
        onHover={handleHover}
        onLeave={handleLeave}
        activePlayer={null}
        setActivePlayer={setActivePlayer}
        nodeMap={{}}
      />
    );

    // Assert cluster stats are visible
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('75')).toBeInTheDocument();
    expect(screen.getByText('count')).toBeInTheDocument();
    expect(screen.getByText('share')).toBeInTheDocument();
    
    // Assert copy button is present
    const copyButton = screen.getByRole('button', { name: /Copy code/i });
    expect(copyButton).toBeInTheDocument();
    
    // Simulate copy click
    fireEvent.click(copyButton);
    expect(handleCopy).toHaveBeenCalledWith('mock-loadout-code-123');
  });
});
