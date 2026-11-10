# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestMailThreadDisableAutoFollowers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user_disable_followers",
                "email": "test_disable_followers@test.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        cls.env["mail.thread.disable.auto.followers.config"].search([]).unlink()
        cls.config = cls.env["mail.thread.disable.auto.followers.config"].search(
            [], limit=1
        )
        if not cls.config:
            cls.config = cls.env["mail.thread.disable.auto.followers.config"].create({})
        cls.model_partner = cls.env["ir.model"].search([("model", "=", "res.partner")])

    def test_01_normal_auto_follower(self):
        """Verify normal behavior where auto-followers are added if not disabled."""
        self.config.write({"model_ids": [(5, 0, 0)]})
        partner_normal = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Partner Normal",
                }
            )
        )
        followers_normal = partner_normal.message_follower_ids.mapped("partner_id")
        self.assertIn(self.test_user.partner_id, followers_normal)

    def test_02_disabled_create(self):
        """Verify record creator is not auto-subscribed on disabled models."""
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})
        partner_disabled = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Partner Disabled",
                }
            )
        )
        followers_disabled = partner_disabled.message_follower_ids.mapped("partner_id")
        self.assertNotIn(self.test_user.partner_id, followers_disabled)

    def test_03_disabled_composer(self):
        """Verify followers are not auto-added via mail.compose.message wizard."""
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})
        partner_disabled = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Partner Disabled Composer",
                }
            )
        )

        composer = (
            self.env["mail.compose.message"]
            .with_user(self.test_user)
            .with_context(
                active_model="res.partner",
                active_ids=partner_disabled.ids,
            )
            .create(
                {
                    "subject": "Test Subject",
                    "body": "Test Body",
                }
            )
        )
        composer._action_send_mail()

        followers_post = partner_disabled.message_follower_ids.mapped("partner_id")
        self.assertNotIn(self.test_user.partner_id, followers_post)

    def test_04_disabled_message_post(self):
        """Verify direct message_post calls do not add the poster as a follower."""
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})
        partner_disabled = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Partner Disabled Post",
                }
            )
        )

        partner_disabled.with_user(self.test_user).message_post(
            body="Direct message",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        followers_after_post = partner_disabled.message_follower_ids.mapped(
            "partner_id"
        )
        self.assertNotIn(self.test_user.partner_id, followers_after_post)

    def test_05_disabled_message_subscribe(self):
        """Verify explicit subscriber additions are bypassed/blocked on
        disabled models.
        """
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})
        partner_disabled = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Partner Disabled Subscribe",
                }
            )
        )

        partner_disabled.with_user(self.test_user).message_subscribe(
            partner_ids=[self.test_user.partner_id.id]
        )
        followers_after_sub = partner_disabled.message_follower_ids.mapped("partner_id")
        self.assertNotIn(self.test_user.partner_id, followers_after_sub)

    def test_06_disabled_write(self):
        """Verify editing fields does not trigger automatic user subscription."""
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})
        partner_disabled = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Partner Disabled Write",
                }
            )
        )

        partner_disabled.with_user(self.test_user).write(
            {
                "name": "Partner Disabled Updated",
            }
        )
        followers_after_write = partner_disabled.message_follower_ids.mapped(
            "partner_id"
        )
        self.assertNotIn(self.test_user.partner_id, followers_after_write)

    def test_07_allow_auto_followers_context(self):
        """Verify override context allows followers again."""
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})

        partner = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .with_context(mail_thread_allow_auto_followers=True)
            .create(
                {
                    "name": "Partner Allow Followers",
                }
            )
        )

        followers = partner.message_follower_ids.mapped("partner_id")
        self.assertIn(self.test_user.partner_id, followers)

    def test_08_message_subscribe_allowed(self):
        """Verify explicit subscribe works when override context is enabled."""
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})

        partner = self.env["res.partner"].create(
            {
                "name": "Partner Subscribe Allowed",
            }
        )

        partner.with_context(mail_thread_allow_auto_followers=True).message_subscribe(
            partner_ids=[self.test_user.partner_id.id]
        )

        followers = partner.message_follower_ids.mapped("partner_id")
        self.assertIn(self.test_user.partner_id, followers)

    def test_09_non_disabled_model(self):
        """Verify normal behavior on models not in config."""
        self.config.write({"model_ids": [(5, 0, 0)]})

        partner = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Normal Partner",
                }
            )
        )

        followers = partner.message_follower_ids.mapped("partner_id")
        self.assertIn(self.test_user.partner_id, followers)

    def test_10_message_post_autofollow_context(self):
        """Verify message_post with mail_post_autofollow=True context
        does not auto-subscribe.
        """
        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})
        partner_disabled = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create(
                {
                    "name": "Partner Disabled Post AutoFollow",
                }
            )
        )
        partner_disabled.with_user(self.test_user).with_context(
            mail_post_autofollow=True
        ).message_post(
            body="Direct message with autofollow",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        followers = partner_disabled.message_follower_ids.mapped("partner_id")
        self.assertNotIn(self.test_user.partner_id, followers)

    def test_11_get_subscription_data_with_followers(self):
        """Verify _get_subscription_data returns filtered results
        when there are followers.
        """
        self.config.write({"model_ids": [(5, 0, 0)]})
        partner = (
            self.env["res.partner"]
            .with_user(self.test_user)
            .create({"name": "Test Partner for Subscription Data"})
        )
        self.assertTrue(partner.message_follower_ids)

        self.config.write({"model_ids": [(6, 0, [self.model_partner.id])]})
        followers_model = self.env["mail.followers"]

        partner_pids = partner.message_follower_ids.mapped("partner_id").ids
        res_normal = followers_model._get_subscription_data(
            [(partner._name, partner.ids)], partner_pids
        )
        self.assertTrue(res_normal)

        res_filtered = followers_model.with_context(
            mail_create_nosubscribe=True,
            active_model=partner._name,
            mail_thread_disable_auto_followers=[partner._name],
        )._get_subscription_data([(partner._name, partner.ids)], partner_pids)
        for row in res_filtered:
            self.assertIsNone(row[2])
