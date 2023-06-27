from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bioblend.galaxy import GalaxyInstance
from . import (
    GalaxyTestBase,
    test_util,
)


class TestGalaxyNotifications(GalaxyTestBase.GalaxyTestBase):
    @test_util.skip_unless_galaxy("release_23.1")
    def test_notification_status(self):
        # WARNING: This test includes user creation
        # and only admins can create users
        # WARNING: Users cannot be purged through the Galaxy API, so execute
        # this test only on a disposable Galaxy instance
        # WARNING: This test sends notifications
        # and only admins can send them
        if self.gi.config.get_config()["use_remote_user"]:
            self.skipTest("This Galaxy instance is not configured to use local users.")
        if not self.gi.config.get_config()["enable_notification_system"]:
            self.skipTest("This Galaxy instance is not configured to use notifications.")
        if not self.gi.users.get_current_user()["is_admin"]:
            self.skipTest("This tests requires the current user to be an admin, which is not the case.")

        # user creation for the test
        user1 = self._create_local_test_user(password="password")
        user2 = self._create_local_test_user(password="password")

        # creating galaxy instances for test
        user1_gi = GalaxyInstance(
            url=self.gi.base_url,
            email=user1["email"],
            password="password",
        )
        user2_gi = GalaxyInstance(
            url=self.gi.base_url,
            email=user2["email"],
            password="password",
        )

        # get the time before creating notifications
        before_creation = datetime.utcnow()

        # Only user1 will receive this notification
        created_response_1 = self._send_test_notification_to(
            [user1["id"]],
            message="test_notification_status 1",
        )
        assert created_response_1["total_notifications_sent"] == 1

        # Both user1 and user2 will receive this notification
        created_response_2 = self._send_test_notification_to(
            [user1["id"], user2["id"]],
            message="test_notification_status 2",
        )
        assert created_response_2["total_notifications_sent"] == 2

        # All users will receive this broadcasted notification
        self._send_test_broadcast_notification(message="test_notification_status 3")

        # user 1 should have received both messages and the broadcast
        status = user1_gi.notifications.get_notification_status(since=before_creation)
        assert status["total_unread_count"] == 2
        status_notifications = status["notifications"]
        assert len(status_notifications) == 2
        assert status_notifications[0]["content"]["message"] == "test_notification_status 1"
        assert len(status["broadcasts"]) == 1
        assert status["broadcasts"][0]["content"]["message"] == "test_notification_status 3"

        # user 2 should have received the second messages and the broadcast
        status = user2_gi.notifications.get_notification_status(since=before_creation)
        assert status["total_unread_count"] == 1
        status_notifications = status["notifications"]
        assert len(status_notifications) == 1
        assert status_notifications[0]["content"]["message"] == "test_notification_status 2"
        assert len(status["broadcasts"]) == 1
        assert status["broadcasts"][0]["content"]["message"] == "test_notification_status 3"

    @test_util.skip_unless_galaxy("release_23.1")
    def test_empty_notification_status(self):
        if not self.gi.config.get_config()["enable_notification_system"]:
            self.skipTest("This Galaxy instance is not configured to use notifications.")

        # fetch the empty notification status
        now = datetime.utcnow()
        status = self.gi.notifications.get_notification_status(since=now)

        # check the datatype
        assert type(status["total_unread_count"]) == int
        assert type(status["broadcasts"]) == list
        assert type(status["notifications"]) == list

        # check if the notification is really empty
        assert status["total_unread_count"] == 0
        assert status["broadcasts"] == []
        assert status["notifications"] == []

    @test_util.skip_unless_galaxy("release_23.1")
    def test_notification_preferences(self):
        if not self.gi.config.get_config()["enable_notification_system"]:
            self.skipTest("This Galaxy instance is not configured to use notifications.")

        # the notification preferences, which should be set to true by default
        preferences = self.gi.notifications.get_notification_preferences()

        # notifications preferences for messages
        message_preferences = preferences["preferences"]["message"]
        assert message_preferences["enabled"] is True
        assert message_preferences["channels"]["push"] is True

        # notifications preferences for new shared items
        new_items_preferences = preferences["preferences"]["new_shared_item"]
        assert new_items_preferences["enabled"] is True
        assert new_items_preferences["channels"]["push"] is True

        # change preferences to False
        self.gi.notifications.update_notification_preferences(
            message_notifications=False,
            push_notifications_message=False,
            new_item_notifications=False,
            push_notifications_new_items=False,
        )

        # check the updated notification preferences
        preferences = self.gi.notifications.get_notification_preferences()
        message_preferences = preferences["preferences"]["message"]
        assert message_preferences["enabled"] is False
        assert message_preferences["channels"]["push"] is False
        new_items_preferences = preferences["preferences"]["new_shared_item"]
        assert new_items_preferences["enabled"] is False
        assert new_items_preferences["channels"]["push"] is False

    @test_util.skip_unless_galaxy("release_23.1")
    def test_get_user_notifications(self):
        # WARNING: This test sends notifications
        # and only admins can send them
        if not self.gi.config.get_config()["enable_notification_system"]:
            self.skipTest("This Galaxy instance is not configured to use notifications.")
        if not self.gi.users.get_current_user()["is_admin"]:
            self.skipTest("This tests requires the current user to be an admin, which is not the case.")

        # send the notifications
        user_id = [self.gi.users.get_current_user()["id"]]
        self._send_test_notification_to(user_id, message="test_notification_status 1")
        self._send_test_notification_to(user_id, message="test_notification_status 2")
        self._send_test_notification_to(user_id, message="test_notification_status 3")

        # this should fetch all the notifications
        created_response_1 = self.gi.notifications.get_user_notifications()

        # this should fetch only the first notification send
        created_response_2 = self.gi.notifications.get_user_notifications(limit=1)

        # this should fetch only the second notification send
        created_response_3 = self.gi.notifications.get_user_notifications(limit=1, offset=1)

        # this should fetch the second and third notifications send
        created_response_4 = self.gi.notifications.get_user_notifications(offset=1)

        # this should fetch nothing, because the first 3 matches are skipped
        # and there are only 3 messages in total
        created_response_5 = self.gi.notifications.get_user_notifications(offset=3)

        # check the amount of messages returned
        assert len(created_response_1) == 3
        assert len(created_response_2) == 1
        assert len(created_response_3) == 1
        assert len(created_response_4) == 2
        assert len(created_response_5) == 0

        # check the content of the first request
        assert created_response_1[0]["content"]["message"] == "test_notification_status 1"
        assert created_response_1[1]["content"]["message"] == "test_notification_status 2"
        assert created_response_1[2]["content"]["message"] == "test_notification_status 3"

        # check the content of the second request
        assert created_response_2[0]["content"]["message"] == "test_notification_status 1"

        # check the content of the third request
        assert created_response_3[0]["content"]["message"] == "test_notification_status 2"

        # check the content of the fourth request
        assert created_response_4[0]["content"]["message"] == "test_notification_status 2"
        assert created_response_4[1]["content"]["message"] == "test_notification_status 3"

    @test_util.skip_unless_galaxy("release_23.1")
    def test_show_notification(self):
        # WARNING: This test sends notifications
        # and only admins can send them
        if not self.gi.config.get_config()["enable_notification_system"]:
            self.skipTest("This Galaxy instance is not configured to use notifications.")
        if not self.gi.users.get_current_user()["is_admin"]:
            self.skipTest("This tests requires the current user to be an admin, which is not the case.")

        # user creation for the test
        user = self._create_local_test_user(password="password")

        # creating galaxy instance for user 1
        user_gi = GalaxyInstance(url=self.gi.base_url, email=user["email"], password="password")

        # send the test notification
        notification_response = self._send_test_notification_to([user["id"]], message="test_notification_status")[
            "notification"
        ]
        notification_id = notification_response["id"]

        # Fetch the notification
        notification = user_gi.notifications.show_notification(notification_id)

        # check that the content is correct
        assert notification["content"]["message"] == "test_notification_status"

    def _send_test_broadcast_notification(
        self,
        subject: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        This is a helper function for sending a test notification.

        :type galaxy_instance: GalaxyInstance
        param galaxy_instance: The GalaxyInstance making the call

        :type subject: str
        param subject: Purpose of the notification

        :type message: str
        param message: Actual content of the notification.

        :rtype: dict
        :return: A dictionary containing the current status
                 summary of notifications
        """
        broadcast = self.gi.notifications.broadcast_notification(
            source="notifications_test",
            message=message or "Testing Message",
            subject=subject or "Testing Subject",
            action_links={
                "link_1": "https://link1.de",
                "link_2": "https://link2.de",
            },
            variant="info",
            expiration_time=(datetime.utcnow() + timedelta(days=1)),
        )
        return broadcast

    def _create_local_test_user(self, password: str) -> Dict[str, Any]:
        new_username = test_util.random_string()
        new_user_email = f"{new_username}@example.org"
        new_user = self.gi.users.create_local_user(new_username, new_user_email, password)
        return new_user

    def _send_test_notification_to(
        self,
        user_ids: List[str],
        subject: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        This is a helper function for sending a test notification.

        :type galaxy_instance: GalaxyInstance
        param galaxy_instance: The GalaxyInstance making the call

        :type user_ids: list
        param user_ids: List of user IDs of users to receive the notification.

        :type subject: str
        param subject: Purpose of the notification

        :type message: str
        param message: Actual content of the notification.

        :rtype: dict
        :return: A dictionary containing the current status summary of notifications.
        """
        notification = self.gi.notifications.send_notification(
            source="notifications_test",
            subject=subject or "Testing Subject",
            message=message or "Testing Message",
            variant="info",
            user_ids=user_ids,
            expiration_time=(datetime.utcnow() + timedelta(days=1)),
        )
        return notification
