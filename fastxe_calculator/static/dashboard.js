(function () {
  const ready = (fn) => {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
    }
  };

  ready(() => {
    const addButton = document.getElementById('add-cost-row');
    const tableBody = document.querySelector('#cost-table tbody');
    const template = document.getElementById('cost-row-template');

    if (!addButton || !tableBody || !template) {
      return;
    }

    addButton.addEventListener('click', () => {
      const clone = template.content.cloneNode(true);
      tableBody.appendChild(clone);
      focusLastRow(tableBody);
    });

    tableBody.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      if (target.classList.contains('remove-cost-row')) {
        const row = target.closest('tr');
        if (!row) {
          return;
        }

        if (tableBody.children.length === 1) {
          row.querySelectorAll('input, select, textarea').forEach((element) => {
            element.value = '';
          });
          return;
        }

        row.remove();
      }
    });
  });

  function focusLastRow(tableBody) {
    const rows = tableBody.querySelectorAll('tr');
    const lastRow = rows[rows.length - 1];
    if (!lastRow) {
      return;
    }
    const firstInput = lastRow.querySelector('input, select, textarea');
    if (firstInput instanceof HTMLElement) {
      firstInput.focus();
    }
  }
})();
