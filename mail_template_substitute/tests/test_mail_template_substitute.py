# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form, TransactionCase


class TestMailTemplateSubstitute(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.smt2 = cls.env["mail.template"].create(
            {
                "name": "substitute_template_2",
                "model_id": cls.env.ref("base.model_res_partner").id,
            }
        )
        cls.smt1 = cls.env["mail.template"].create(
            {
                "name": "substitute_template_1",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "mail_template_substitution_rule_ids": [
                    (
                        0,
                        0,
                        {
                            "substitution_mail_template_id": cls.smt2.id,
                            "domain": "[('id', '=', False)]",
                        },
                    )
                ],
            }
        )
        cls.mt = cls.env["mail.template"].create(
            {
                "name": "base_template",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "mail_template_substitution_rule_ids": [
                    (0, 0, {"substitution_mail_template_id": cls.smt1.id})
                ],
            }
        )
        cls.mail_compose = cls.env["mail.compose.message"].create(
            {"template_id": cls.mt.id, "composition_mode": "mass_mail"}
        )
        cls.partners = cls.env["res.partner"].search([])
        cls.partner = cls.env["res.partner"].search([], limit=1)

    def test_get_email_template_partners(self):
        self.assertEqual(
            self.mt._get_substitution_template(
                self.env.ref("base.model_res_partner"), self.partners.ids
            ),
            self.smt1,
        )
        res_ids_to_templates = self.mt._classify_per_lang(self.partners.ids)
        self.assertTrue(len(res_ids_to_templates))
        _lang, (template, _res_ids) = list(res_ids_to_templates.items())[0]
        self.assertEqual(
            template,
            self.smt1,
        )

    def test_get_email_template_partner(self):
        self.assertEqual(
            self.mt._get_substitution_template(
                self.env.ref("base.model_res_partner"), self.partner.ids
            ),
            self.smt1,
        )
        res_ids_to_templates = self.mt._classify_per_lang(self.partner.ids)
        self.assertTrue(len(res_ids_to_templates))
        _lang, (template, _res_ids) = list(res_ids_to_templates.items())[0]
        self.assertEqual(
            template,
            self.smt1,
        )

    def test_get_substitution_template(self):
        self.assertEqual(
            self.mail_compose.with_context(
                active_ids=self.partners.ids
            )._get_substitution_template("mass_mail", self.mt, None),
            self.smt1,
        )

    def test_default_get(self):
        mail_compose_form = Form(
            self.env["mail.compose.message"].with_context(
                **{
                    "default_template_id": self.mt.id,
                    "default_model": self.partner._name,
                    "default_res_ids": self.partner.ids,
                }
            )
        )
        self.assertEqual(mail_compose_form.template_id, self.smt1)

    def test_get_substitution_template_account_move_send(self):
        account_id = (
            self.env["account.account"]
            .search([("account_type", "=", "asset_receivable")], limit=1)
            .id
        )
        move = self.env["account.move"].create(
            {
                "name": "Test Move",
                "journal_id": self.env["account.journal"].search([], limit=1).id,
                "date": "2024-01-01",
                "move_type": "out_invoice",  # Asegúrate de que sea una factura
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": account_id,
                        },
                    )
                ],
            }
        )
        move.action_post()
        wizard = (
            self.env["account.move.send.wizard"]
            .with_context(active_ids=[move.id])
            .create({})
        )
        template = self.env["mail.template"].create(
            {
                "name": "Test Template",
                "model_id": self.env.ref("account.model_account_move").id,
            }
        )
        res = wizard._get_substitution_template(template, [move.id])
        self.assertTrue(res == template or res is False)

    def test_compute_mail_template_id(self):
        """Test el cálculo del template por defecto en account.move.send.wizard"""
        # Crear un template adicional para facturas
        self.env["mail.template"].create(
            {
                "name": "Test Invoice Template",
                "model_id": self.env.ref("account.model_account_move").id,
            }
        )

        # Crear una factura utilizando la configuración de setUp
        account_id = (
            self.env["account.account"]
            .search([("account_type", "=", "asset_receivable")], limit=1)
            .id
        )
        move = self.env["account.move"].create(
            {
                "name": "Test Move",
                "journal_id": self.env["account.journal"].search([], limit=1).id,
                "date": "2024-01-01",
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": account_id,
                        },
                    )
                ],
            }
        )
        move.action_post()

        # Crear el wizard y obtener el template por defecto
        wizard = (
            self.env["account.move.send.wizard"]
            .with_context(active_ids=[move.id])
            .create({})
        )
        original_template = wizard.mail_template_id

        # Crear un template de sustitución
        template2 = self.env["mail.template"].create(
            {
                "name": "Substitution Invoice Template",
                "model_id": self.env.ref("account.model_account_move").id,
            }
        )

        # Añadir regla de sustitución al template original
        original_template.write(
            {
                "mail_template_substitution_rule_ids": [
                    (
                        0,
                        0,
                        {
                            "substitution_mail_template_id": template2.id,
                            "domain": f"[('id', '=', {move.id})]",
                        },
                    )
                ],
            }
        )

        # Crear un nuevo wizard y verificar si aplica la sustitución
        wizard2 = (
            self.env["account.move.send.wizard"]
            .with_context(active_ids=[move.id])
            .create({})
        )

        # Comprobar que mail_template_id es ahora el template de sustitución
        self.assertEqual(wizard2.mail_template_id, template2)
