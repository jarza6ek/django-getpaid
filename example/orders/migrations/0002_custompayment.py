# Generated by Django 2.0.7 on 2018-08-08 08:52

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [("orders", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="CustomPayment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=4, max_digits=20, verbose_name="amount"
                    ),
                ),
                ("currency", models.CharField(max_length=3, verbose_name="currency")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "new"),
                            ("in_progress", "in progress"),
                            ("accepted_for_proc", "accepted for processing"),
                            ("partially_paid", "partially paid"),
                            ("paid", "paid"),
                            ("cancelled", "cancelled"),
                            ("failed", "failed"),
                        ],
                        db_index=True,
                        default="new",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                ("backend", models.CharField(max_length=50, verbose_name="backend")),
                (
                    "created_on",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="created on"
                    ),
                ),
                (
                    "paid_on",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        default=None,
                        null=True,
                        verbose_name="paid on",
                    ),
                ),
                (
                    "amount_paid",
                    models.DecimalField(
                        decimal_places=4,
                        default=0,
                        max_digits=20,
                        verbose_name="amount paid",
                    ),
                ),
                (
                    "external_id",
                    models.CharField(
                        blank=True, max_length=64, null=True, verbose_name="external id"
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        max_length=128,
                        null=True,
                        verbose_name="description",
                    ),
                ),
                ("custom", models.BooleanField(default=True, editable=False)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="orders.Order",
                        verbose_name="order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Payment",
                "verbose_name_plural": "Payments",
                "ordering": ["-created_on"],
                "abstract": False,
            },
        )
    ]