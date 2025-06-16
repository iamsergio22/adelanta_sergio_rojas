from odoo import models, fields

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    applicable_user_levels = fields.Many2many(
        'adelanta.user.level',
        string='Niveles Permitidos'
    )

    def _compute_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency, cash_rounding=None):
        """Get the distribution of this payment term.
        :param date_ref: The move date to take into account
        :param currency: the move's currency
        :param company: the company issuing the move
        :param tax_amount: the signed tax amount for the move
        :param tax_amount_currency: the signed tax amount for the move in the move's currency
        :param untaxed_amount: the signed untaxed amount for the move
        :param untaxed_amount_currency: the signed untaxed amount for the move in the move's currency
        :param sign: the sign of the move
        :param cash_rounding: the cash rounding that should be applied (or None).
            We assume that the input total in move currency (tax_amount_currency + untaxed_amount_currency) is already cash rounded.
            The cash rounding does not change the totals: Consider the sum of all the computed payment term amounts in move / company currency.
            It is the same as the input total in move / company currency.
        :return (list<tuple<datetime.date,tuple<float,float>>>): the amount in the company's currency and
            the document's currency, respectively for each required payment date
        """
        self.ensure_one()
        company_currency = company.currency_id
        tax_amount_left = tax_amount
        tax_amount_currency_left = tax_amount_currency
        untaxed_amount_left = untaxed_amount
        untaxed_amount_currency_left = untaxed_amount_currency
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency
        foreign_rounding_amount = 0
        company_rounding_amount = 0
        result = []

        # ---------------------- added these lines ----------------------
        initial_fee = 0.0
        invoice=self.env.context['invoice'] if 'invoice' in self.env.context else None
        values_level = {
            'nivel_1': 0.6,
            'nivel_2': 0.5,
            'nivel_3': 0.4,
        }
        if invoice and invoice.partner_id and invoice.partner_id.user_level_id:
            result.append({
                'date': invoice.invoice_date or fields.Date.context_today(self), 
                'has_discount': 0.0, 
                'discount_date': None, 
                'discount_amount_currency': 0.0, 
                'discount_balance': 0.0, 
                'discount_percentage': 0.0, 
                'company_amount': 0.0, 
                'foreign_amount': total_amount * values_level[invoice.partner_id.user_level_id.code]
            })
            initial_fee = result[0]['foreign_amount']
            total_amount_currency -= initial_fee
            total_amount -= initial_fee
        # ---------------------------------------------------

        for line in self.line_ids.sorted(lambda line: line.value == 'balance'):
            term_vals = {
                'date': line._get_due_date(date_ref),
                'has_discount': line.discount_percentage,
                'discount_date': None,
                'discount_amount_currency': 0.0,
                'discount_balance': 0.0,
                'discount_percentage': line.discount_percentage,
            }

            if line.value == 'fixed':
                term_vals['company_amount'] = sign * company_currency.round(line.value_amount)
                term_vals['foreign_amount'] = sign * currency.round(line.value_amount)
                company_proportion = tax_amount/untaxed_amount if untaxed_amount else 1
                foreign_proportion = tax_amount_currency/untaxed_amount_currency if untaxed_amount_currency else 1
                line_tax_amount = company_currency.round(line.value_amount * company_proportion) * sign
                line_tax_amount_currency = currency.round(line.value_amount * foreign_proportion) * sign
                line_untaxed_amount = term_vals['company_amount'] - line_tax_amount
                line_untaxed_amount_currency = term_vals['foreign_amount'] - line_tax_amount_currency
            elif line.value == 'percent':
                term_vals['company_amount'] = company_currency.round(total_amount * (line.value_amount / 100.0))
                term_vals['foreign_amount'] = currency.round(total_amount_currency * (line.value_amount / 100.0))
                line_tax_amount = company_currency.round(tax_amount * (line.value_amount / 100.0))
                line_tax_amount_currency = currency.round(tax_amount_currency * (line.value_amount / 100.0))
                line_untaxed_amount = term_vals['company_amount'] - line_tax_amount
                line_untaxed_amount_currency = term_vals['foreign_amount'] - line_tax_amount_currency
            else:
                line_tax_amount = line_tax_amount_currency = line_untaxed_amount = line_untaxed_amount_currency = 0.0

            # The following values do not account for any potential cash rounding
            tax_amount_left -= line_tax_amount
            tax_amount_currency_left -= line_tax_amount_currency
            untaxed_amount_left -= line_untaxed_amount
            untaxed_amount_currency_left -= line_untaxed_amount_currency

            if cash_rounding and line.value in ['fixed', 'percent']:
                cash_rounding_difference_currency = cash_rounding.compute_difference(currency, term_vals['foreign_amount'])
                if not currency.is_zero(cash_rounding_difference_currency):
                    rate = abs(term_vals['foreign_amount'] / term_vals['company_amount']) if term_vals['company_amount'] else 1.0

                    foreign_rounding_amount += cash_rounding_difference_currency
                    term_vals['foreign_amount'] += cash_rounding_difference_currency

                    company_amount = company_currency.round(term_vals['foreign_amount'] / rate)
                    cash_rounding_difference = company_amount - term_vals['company_amount']
                    if not currency.is_zero(cash_rounding_difference):
                        company_rounding_amount += cash_rounding_difference
                        term_vals['company_amount'] = company_amount

            if line.value == 'balance':
                # The `*_amount_left` variables do not account for cash rounding.
                # Here we remove the total amount added by the cash rounding from the amount left.
                # This way the totals in company and move currency remain unchanged (compared to the input).
                # We assume the foreign total (`tax_amount_currency + untaxed_amount_currency`) is cash rounded.
                # The following right side is the same as subtracting all the (cash rounded) foreign payment term amounts from the foreign total.
                # Thus it is the remaining foreign amount and also cash rounded.
                term_vals['foreign_amount'] = tax_amount_currency_left + untaxed_amount_currency_left - foreign_rounding_amount - initial_fee
                term_vals['company_amount'] = tax_amount_left + untaxed_amount_left - company_rounding_amount - initial_fee

                line_tax_amount = tax_amount_left
                line_tax_amount_currency = tax_amount_currency_left
                line_untaxed_amount = untaxed_amount_left
                line_untaxed_amount_currency = untaxed_amount_currency_left

            if line.discount_percentage:
                if company.early_pay_discount_computation in ('excluded', 'mixed'):
                    term_vals['discount_balance'] = company_currency.round(term_vals['company_amount'] - line_untaxed_amount * line.discount_percentage / 100.0)
                    term_vals['discount_amount_currency'] = currency.round(term_vals['foreign_amount'] - line_untaxed_amount_currency * line.discount_percentage / 100.0)
                else:
                    term_vals['discount_balance'] = company_currency.round(term_vals['company_amount'] * (1 - (line.discount_percentage / 100.0)))
                    term_vals['discount_amount_currency'] = currency.round(term_vals['foreign_amount'] * (1 - (line.discount_percentage / 100.0)))
                term_vals['discount_date'] = date_ref + relativedelta(days=line.discount_days)

            if cash_rounding and line.discount_percentage:
                cash_rounding_difference_currency = cash_rounding.compute_difference(currency, term_vals['discount_amount_currency'])
                if not currency.is_zero(cash_rounding_difference_currency):
                    rate = abs(term_vals['discount_amount_currency'] / term_vals['discount_balance']) if term_vals['discount_balance'] else 1.0
                    term_vals['discount_amount_currency'] += cash_rounding_difference_currency
                    term_vals['discount_balance'] = company_currency.round(term_vals['discount_amount_currency'] / rate)

            result.append(term_vals)
        return result
