import { NgModule } from '@angular/core';
import { AsyncKeyValueStorage } from './storage.model';
import { AsyncLocalStorageService } from './async-local-storage.service';
import { LOCAL_STORAGE, SESSION_STORAGE, localStorageFactory, sessionStorageFactory } from './browser-storage.service';
import { StorageMigrationService } from './storage-migration.service';

@NgModule({
  providers: [
    { provide: LOCAL_STORAGE, useFactory: localStorageFactory },
    { provide: SESSION_STORAGE, useFactory: sessionStorageFactory },
    { provide: AsyncKeyValueStorage, useClass: AsyncLocalStorageService },
    StorageMigrationService,
  ],
})
export class StorageModule {}
