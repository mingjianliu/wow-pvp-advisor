import React from 'react';
import ReactDOM from 'react-dom';
import { vi } from 'vitest';

globalThis.React = React;
globalThis.ReactDOM = ReactDOM;

globalThis.window.location = {
  pathname: '/index.html'
};

globalThis.window.t = (key) => key;
globalThis.t = (key) => key;

globalThis.fetch = vi.fn().mockImplementation(() =>
  Promise.resolve({
    json: () => Promise.resolve({ icon: 'mock-icon', name: 'Mock Spell', tooltip: '<div>Mock Tooltip</div>' })
  })
);
