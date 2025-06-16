from odoo import models, fields, api

class PaymentStatusTracking(models.Model):
    _name = 'payment.status.tracking'
    _description = 'Tracking de estados de pago'
    _auto = False  

    id = fields.Integer('ID', readonly=True)
    fecha = fields.Date("Fecha del Cambio")
    estado_pago = fields.Selection(selection=[
        ('not_paid', 'No pagadas'),
        ('in_payment', 'En proceso de pago'),
        ('paid', 'Pagado'),
        ('partial', 'Pagado Parcialmente'),
        ('reversed', 'Revertido'),
        ('undefined', 'Indefinido'),
    ])
    cantidad = fields.Integer("Cantidad de cambios")    

    def init(self):
        self.env.cr.execute("""DROP VIEW IF EXISTS payment_status_tracking CASCADE""")
        self.env.cr.execute("""
        CREATE OR REPLACE VIEW payment_status_tracking AS (
            SELECT
                row_number() OVER () AS id,
                fecha,
                estado_pago,
                SUM(cantidad) AS cantidad
            FROM (
                
                SELECT
                    date(mm.create_date) AS fecha,
                    CASE
                        WHEN LOWER(mtv.new_value_char) = 'not paid' THEN 'not_paid'
                        WHEN LOWER(mtv.new_value_char) = 'in payment' THEN 'in_payment'
                        WHEN LOWER(mtv.new_value_char) = 'paid' THEN 'paid'
                        WHEN LOWER(mtv.new_value_char) = 'partially paid' THEN 'partial'
                        WHEN LOWER(mtv.new_value_char) = 'reversed' THEN 'reversed'
                        ELSE 'undefined'
                    END AS estado_pago,
                    COUNT(*) AS cantidad
                FROM
                    mail_tracking_value mtv
                JOIN
                    mail_message mm ON mm.id = mtv.mail_message_id
                JOIN
                    ir_model_fields imf ON imf.id = mtv.field
                WHERE
                    imf.name = 'payment_state'
                    AND mm.model = 'account.move'
                    AND mtv.new_value_char IS NOT NULL
                GROUP BY
                    date(mm.create_date),
                    CASE
                        WHEN LOWER(mtv.new_value_char) = 'not paid' THEN 'not_paid'
                        WHEN LOWER(mtv.new_value_char) = 'in payment' THEN 'in_payment'
                        WHEN LOWER(mtv.new_value_char) = 'paid' THEN 'paid'
                        WHEN LOWER(mtv.new_value_char) = 'partially paid' THEN 'partial'
                        WHEN LOWER(mtv.new_value_char) = 'reversed' THEN 'reversed'
                        ELSE 'undefined'
                    END

                UNION ALL

                
                SELECT
                    date(am.create_date) AS fecha,
                    CASE
                        WHEN am.payment_state = 'not_paid' THEN 'not_paid'
                        WHEN am.payment_state = 'in_payment' THEN 'in_payment'
                        WHEN am.payment_state = 'paid' THEN 'paid'
                        WHEN am.payment_state = 'partial' THEN 'partial'
                        WHEN am.payment_state = 'reversed' THEN 'reversed'
                        ELSE 'undefined'
                    END AS estado_pago,
                    COUNT(*) AS cantidad
                FROM
                    account_move am
                WHERE
                    am.move_type IN ('out_invoice', 'out_refund')
                    AND am.payment_state IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1
                        FROM mail_message mm
                        JOIN mail_tracking_value mtv ON mtv.mail_message_id = mm.id
                        JOIN ir_model_fields imf ON imf.id = mtv.field
                        WHERE
                            mm.model = 'account.move'
                            AND mm.res_id = am.id
                            AND imf.name = 'payment_state'
                    )
                GROUP BY
                    date(am.create_date),
                    CASE
                        WHEN am.payment_state = 'not_paid' THEN 'not_paid'
                        WHEN am.payment_state = 'in_payment' THEN 'in_payment'
                        WHEN am.payment_state = 'paid' THEN 'paid'
                        WHEN am.payment_state = 'partial' THEN 'partial'
                        WHEN am.payment_state = 'reversed' THEN 'reversed'
                        ELSE 'undefined'
                    END
            ) AS subquery
            GROUP BY fecha, estado_pago
            ORDER BY fecha
        );
    """)