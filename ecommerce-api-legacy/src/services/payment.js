// Local demonstration only: no gateway call and no storage/logging of card data.
const PAYMENT_PAID = 'PAID';
const PAYMENT_DENIED = 'DENIED';

function simulatePayment(card) {
    return card.startsWith('4') ? PAYMENT_PAID : PAYMENT_DENIED;
}

module.exports = { simulatePayment, PAYMENT_PAID };
