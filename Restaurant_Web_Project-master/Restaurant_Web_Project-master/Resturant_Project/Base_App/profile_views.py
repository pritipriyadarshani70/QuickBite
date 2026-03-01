from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from Base_App.models import CustomerProfile, Order, OrderItem, Items, Cart, BookTable
from django.db.models import Sum, Count
from datetime import datetime, timedelta
import json


@login_required
def profile_view(request):
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)
    
    # Get order statistics
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    recent_orders = orders[:5]
    
    # Get favorite items
    favorite_items = profile.favorite_items.all()
    
    # Get booking history
    bookings = BookTable.objects.filter(Email=request.user.email).order_by('-Booking_date')[:5]
    
    context = {
        'profile': profile,
        'orders': orders,
        'recent_orders': recent_orders,
        'favorite_items': favorite_items,
        'bookings': bookings,
        'total_orders': orders.count(),
        'total_spent': sum(order.total_amount for order in orders),
        'loyalty_points': profile.loyalty_points,
    }
    
    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    profile = get_object_or_404(CustomerProfile, user=request.user)
    
    if request.method == 'POST':
        profile.phone = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.postal_code = request.POST.get('postal_code', '')
        
        # Update user info
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        
        profile.save()
        request.user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'edit_profile.html', {'profile': profile})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    return render(request, 'order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    
    return render(request, 'order_detail.html', {
        'order': order,
        'order_items': order_items
    })


@login_required
def add_to_favorites(request, item_id):
    item = get_object_or_404(Items, id=item_id)
    profile = get_object_or_404(CustomerProfile, user=request.user)
    
    if item in profile.favorite_items.all():
        profile.favorite_items.remove(item)
        message = f"{item.Item_name} removed from favorites"
    else:
        profile.favorite_items.add(item)
        # Add loyalty points for adding favorite
        profile.loyalty_points += 5
        profile.save()
        message = f"{item.Item_name} added to favorites! +5 points"
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'message': message, 'status': 'success'})
    
    messages.info(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'menu'))


@login_required
def reorder(request, order_id):
    old_order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Add all items from old order to cart
    for order_item in old_order.orderitem_set.all():
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            item=order_item.item,
            defaults={'quantity': order_item.quantity}
        )
        
        if not created:
            cart_item.quantity += order_item.quantity
            cart_item.save()
    
    messages.success(request, 'All items from previous order added to cart!')
    return redirect('menu')


@login_required
def dashboard(request):
    profile = get_object_or_404(CustomerProfile, user=request.user)
    
    # Get statistics
    total_orders = Order.objects.filter(user=request.user).count()
    total_spent = Order.objects.filter(user=request.user).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Recent activity
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:3]
    recent_bookings = BookTable.objects.filter(Email=request.user.email).order_by('-Booking_date')[:3]
    
    # Favorite categories
    favorite_categories = Items.objects.filter(
        orderitem__order__user=request.user
    ).values('Category__Category_name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'profile': profile,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
        'recent_bookings': recent_bookings,
        'favorite_categories': favorite_categories,
    }
    
    return render(request, 'dashboard.html', context)
