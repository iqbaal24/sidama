from django.urls import path

from apps.finance import views

app_name = "finance"

urlpatterns = [
    path("app/transaksi/", views.TransactionListView.as_view(), name="transaction_list"),
    path("app/transaksi/baru/", views.TransactionCreateView.as_view(), name="transaction_create"),
    path("app/transaksi/<int:pk>/", views.TransactionDetailView.as_view(), name="transaction_detail"),
    path("app/transaksi/<int:pk>/ubah/", views.TransactionUpdateView.as_view(), name="transaction_update"),
    path("app/transaksi/<int:pk>/hapus/", views.TransactionDeleteView.as_view(), name="transaction_delete"),
    path("app/transaksi/<int:pk>/pembalik/", views.TransactionReverseView.as_view(), name="transaction_reverse"),
    path("app/transaksi/<int:pk>/setujui/", views.ApproveTransactionView.as_view(), name="transaction_approve"),
    path("app/transaksi/<int:pk>/tolak/", views.RejectTransactionView.as_view(), name="transaction_reject"),
    path("app/persetujuan/", views.ApprovalQueueView.as_view(), name="approval_queue"),
    path("app/dana/", views.FundListView.as_view(), name="fund_list"),
    path("app/dana/baru/", views.FundCreateView.as_view(), name="fund_create"),
    path("app/dana/<int:pk>/ubah/", views.FundUpdateView.as_view(), name="fund_update"),
    path("app/kategori/", views.CategoryListView.as_view(), name="category_list"),
    path("app/kategori/baru/", views.CategoryCreateView.as_view(), name="category_create"),
    path("app/kategori/<int:pk>/ubah/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("app/periode/", views.PeriodListView.as_view(), name="period_list"),
    path("app/periode/tutup/", views.ClosePeriodView.as_view(), name="period_close"),
    path("app/periode/<int:pk>/buka/", views.ReopenPeriodView.as_view(), name="period_reopen"),
]
