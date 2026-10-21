import '@angular/compiler';
import 'zone.js';
import { bootstrapApplication } from '@angular/platform-browser';
import { DemoComponent, demoProviders } from './demo.providers';

bootstrapApplication(DemoComponent, { providers: demoProviders }).catch((error) => console.error(error));
