import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { observationReducer, initialUiState, type ObservationUiState } from '../src/reducer.js';
import type { EvolutionEventEnvelope } from '../src/contracts/envelope.js';
const here = dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(readFileSync(resolve(here, './fixtures/reducer_vectors.json'), 'utf-8')) as Record<string, { events: EvolutionEventEnvelope[]; expected: ObservationUiState }>;
describe('observationReducer ≡ platform CompositeObservationReducer', () => {
  for (const [name, { events, expected }] of Object.entries(vectors)) {
    it(`matches platform fold: ${name}`, () => {
      const finalState = events.reduce((state, envelope) => observationReducer(state, envelope), initialUiState());
      expect(finalState).toEqual(expected);
    });
  }
  it('fails loudly if the fixture is missing vectors', () => {
    expect(Object.keys(vectors).length).toBeGreaterThan(0);
  });
});
