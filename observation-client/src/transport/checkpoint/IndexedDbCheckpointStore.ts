import type { CheckpointRecord, CheckpointStore } from './CheckpointStore.js';

/** Browser persistence. Safe to import anywhere; touches indexedDB lazily. */
export class IndexedDbCheckpointStore<TState> implements CheckpointStore<TState> {
  private dbPromise: Promise<IDBDatabase> | null = null;

  constructor(
    private readonly dbName = 'esap-observation',
    private readonly storeName = 'checkpoints',
  ) {}

  async save(record: CheckpointRecord<TState>): Promise<void> {
    const db = await this.db();
    await this.tx(db, 'readwrite', (store) => {
      store.put(record);
    });
  }

  async load(streamId: string): Promise<CheckpointRecord<TState> | null> {
    const db = await this.db();
    return this.tx(db, 'readonly', (store) => store.get(streamId)) as Promise<
      CheckpointRecord<TState> | null
    >;
  }

  async clear(streamId: string): Promise<void> {
    const db = await this.db();
    await this.tx(db, 'readwrite', (store) => {
      store.delete(streamId);
    });
  }

  private db(): Promise<IDBDatabase> {
    if (!this.dbPromise) {
      this.dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
        if (typeof indexedDB === 'undefined') {
          reject(new Error('IndexedDB is unavailable in this environment'));
          return;
        }
        const request = indexedDB.open(this.dbName, 1);
        request.onupgradeneeded = () => {
          const db = request.result;
          if (!db.objectStoreNames.contains(this.storeName)) {
            db.createObjectStore(this.storeName, { keyPath: 'streamId' });
          }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error ?? new Error('IndexedDB open failed'));
      });
    }
    return this.dbPromise;
  }

  private tx(
    db: IDBDatabase,
    mode: IDBTransactionMode,
    op: (store: IDBObjectStore) => IDBRequest | void,
  ): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(this.storeName, mode);
      const store = transaction.objectStore(this.storeName);
      const request = op(store);
      let result: unknown = null;
      if (request) {
        request.onsuccess = () => {
          result = request.result;
        };
      }
      transaction.oncomplete = () => resolve(result);
      transaction.onerror = () => reject(transaction.error ?? new Error('IndexedDB tx failed'));
      transaction.onabort = () => reject(transaction.error ?? new Error('IndexedDB tx aborted'));
    });
  }
}