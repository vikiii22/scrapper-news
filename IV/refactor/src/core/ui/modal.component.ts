import { Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'tl-modal-dialog',
  standalone: true,
  template: '<ng-content />',
})
export class ModalComponent {
  @Output() readonly closed = new EventEmitter<unknown>();

  close(result?: unknown): void {
    this.closed.emit(result);
  }

  dismiss(result?: unknown): void {
    this.closed.emit(result);
  }
}
