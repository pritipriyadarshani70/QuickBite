from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from Base_App.views import *
from Base_App.profile_views import *
from Base_App.review_views import *

urlpatterns = [
    path('admin/', admin.site.urls, name='admin_pannel'),
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', SignupView, name='signup'),
    path('logout/', LogoutView, name='logout'),
    path('', HomeView, name='Home'),
    path('home/', HomeView, name='Home_alt'),  # Alternative home URL
    path('book_table/', BookTableView, name='Book_Table'),
    path('menu/', MenuView, name='Menu'),
    path('about/', AboutView, name='About'),
    path('feedback/', FeedbackView, name='Feedback_Form'),
    path('add-to-cart/', add_to_cart, name='add_to_cart'),
    path('get-cart-items/', get_cart_items, name='get_cart_items'),
    
    # Profile URLs
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('orders/', order_history, name='order_history'),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
    path('favorites/add/<int:item_id>/', add_to_favorites, name='add_to_favorites'),
    path('reorder/<int:order_id>/', reorder, name='reorder'),
    path('dashboard/', dashboard, name='dashboard'),
    
    # Review URLs
    path('reviews/add/<int:item_id>/', add_review, name='add_review'),
    path('reviews/item/<int:item_id>/', item_reviews, name='item_reviews'),
    path('reviews/vote/<int:review_id>/', vote_review, name='vote_review'),
    path('reviews/delete/<int:review_id>/', delete_review, name='delete_review'),
    
    # Admin Dashboard
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    
    # Checkout
    path('checkout/', checkout, name='checkout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
