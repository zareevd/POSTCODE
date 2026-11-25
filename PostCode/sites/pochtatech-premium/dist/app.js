const detailsDialog = document.querySelector('.details-dialog');
const openButton = document.querySelector('[data-open-details]');

openButton.addEventListener('click', () => detailsDialog.showModal());
document.querySelectorAll('[data-close-details]').forEach(button => {
  button.addEventListener('click', () => detailsDialog.close());
});

detailsDialog.addEventListener('click', event => {
  const bounds = detailsDialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) {
    detailsDialog.close();
  }
});

detailsDialog.addEventListener('close', () => openButton.focus());

const calculator = document.querySelector('[data-savings-calculator]');
const creditButtons = [...calculator.querySelectorAll('[data-credits]')];
const monthlyPrice = Number(calculator.dataset.monthlyPrice);
const creditValue = Number(calculator.dataset.creditValue);
const creditLimit = Number(calculator.dataset.creditLimit);
const rubles = value => `${value < 0 ? '−' : ''}${new Intl.NumberFormat('ru-RU').format(Math.abs(value))} ₽`;

creditButtons.forEach(button => {
  button.addEventListener('click', () => {
    const credits = Math.max(0, Math.min(creditLimit, Number(button.dataset.credits)));
    const benefit = credits * creditValue;
    const netSavings = benefit - monthlyPrice;
    creditButtons.forEach(option => option.setAttribute('aria-pressed', String(option === button)));
    calculator.querySelector('[data-credit-benefit]').textContent = rubles(benefit);
    const result = calculator.querySelector('[data-net-savings]');
    result.textContent = rubles(netSavings);
    result.dataset.value = String(netSavings);
    result.classList.toggle('negative', netSavings < 0);
    calculator.querySelector('[data-result-label]').textContent = netSavings >= 0
      ? 'Экономия после оплаты подписки'
      : 'Результат с учётом платы за подписку';
  });
});
