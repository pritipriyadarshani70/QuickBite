from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView as AuthLoginView
from Base_App.models import BookTable, AboutUs, Feedback, ItemList, Items, Cart
from Base_App.forms import CustomUserCreationForm
from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt

# Admin Dashboard View
@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    """Admin dashboard with analytics"""
    
    # Get date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Order statistics
    total_orders = Cart.objects.count()
    today_orders = Cart.objects.filter(created_at__date=today).count()
    week_orders = Cart.objects.filter(created_at__date__gte=week_ago).count()
    month_orders = Cart.objects.filter(created_at__date__gte=month_ago).count()
    
    # Revenue calculations
    total_revenue = Cart.objects.aggregate(total=Sum('item__Price'))['total'] or 0
    today_revenue = Cart.objects.filter(created_at__date=today).aggregate(total=Sum('item__Price'))['total'] or 0
    week_revenue = Cart.objects.filter(created_at__date__gte=week_ago).aggregate(total=Sum('item__Price'))['total'] or 0
    month_revenue = Cart.objects.filter(created_at__date__gte=month_ago).aggregate(total=Sum('item__Price'))['total'] or 0
    
    # Popular items
    popular_items = Items.objects.annotate(
        order_count=Count('cart')
    ).order_by('-order_count')[:5]
    
    # Recent orders
    recent_orders = Cart.objects.select_related('user', 'item').order_by('-created_at')[:10]
    
    # Table bookings
    total_bookings = BookTable.objects.count()
    today_bookings = BookTable.objects.filter(Booking_date=today).count()
    pending_bookings = BookTable.objects.filter(Booking_date__gte=today).count()
    
    # Customer stats
    total_customers = Cart.objects.values('user').distinct().count()
    
    # Feedback stats
    total_reviews = Feedback.objects.count()
    avg_rating = Feedback.objects.aggregate(avg=Avg('Rating'))['avg'] or 0
    
    context = {
        'total_orders': total_orders,
        'today_orders': today_orders,
        'week_orders': week_orders,
        'month_orders': month_orders,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'popular_items': popular_items,
        'recent_orders': recent_orders,
        'total_bookings': total_bookings,
        'today_bookings': today_bookings,
        'pending_bookings': pending_bookings,
        'total_customers': total_customers,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
    }
    
    return render(request, 'admin/dashboard.html', context)

@csrf_exempt
def add_to_cart(request):
    if request.method == 'POST' and request.user.is_authenticated:
        item_id = request.POST.get('item_id')
        item = get_object_or_404(Items, id=item_id)
        
        # Create cart entry with timestamp
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            item=item,
            defaults={'quantity': 1}
        )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        return JsonResponse({
            'message': 'Item added to cart', 
            'cart_count': Cart.objects.filter(user=request.user).count()
        })
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)


def get_cart_items(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user).select_related('item')
        items = [
            {
                'name': cart_item.item.Item_name,
                'quantity': cart_item.quantity,
                'price': cart_item.item.Price,
                'total': cart_item.quantity * cart_item.item.Price,
            }
            for cart_item in cart_items
        ]
        return JsonResponse({'items': items}, safe=False)
    return JsonResponse({'error': 'User not authenticated'}, status=401)

class LoginView(AuthLoginView):
    template_name = 'login.html'
    def get_success_url(self):
        # Check if the user is an admin
        if self.request.user.is_staff:
            return reverse_lazy('admin:index')  # Redirects to the Django admin panel
        return reverse_lazy('Home')  # Redirects to the home page if not an admin

def LogoutView(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('Home')  # Redirect to a page after logout, e.g., the home page

def SignupView(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        print(f"POST data: {request.POST}")
        print(f"Form is valid: {form.is_valid()}")
        if form.errors:
            print(f"Form errors: {form.errors}")
        if form.is_valid():
            user = form.save()
            print(f"User created: {user.username}")
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('Home')
        else:
            messages.error(request, 'Error during signup. Please check the form below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'login.html', {'form': form, 'tab': 'signup'})


def HomeView(request):
    items =  Items.objects.all()
    list = ItemList.objects.all()
    review = Feedback.objects.all().order_by('-id')[:5]
    return render(request, 'home.html',{'items': items, 'list': list, 'review': review})


def AboutView(request):
    data = AboutUs.objects.all()
    return render(request, 'about.html',{'data': data})


def MenuView(request):
    items =  Items.objects.all()
    list = ItemList.objects.all()
    return render(request, 'menu.html', {'items': items, 'list': list})


@csrf_exempt
def BookTableView(request):
    # Pass API key to the template
    google_maps_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    # Get available time slots
    from Base_App.models import TimeSlot
    available_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    # Create default time slots if none exist
    if not available_slots.exists():
        from datetime import time
        default_slots = [
            (time(11, 0), time(12, 0)),   # 11:00 AM - 12:00 PM
            (time(12, 0), time(13, 0)),   # 12:00 PM - 1:00 PM
            (time(13, 0), time(14, 0)),   # 1:00 PM - 2:00 PM
            (time(18, 0), time(19, 0)),   # 6:00 PM - 7:00 PM
            (time(19, 0), time(20, 0)),   # 7:00 PM - 8:00 PM
            (time(20, 0), time(21, 0)),   # 8:00 PM - 9:00 PM
            (time(21, 0), time(22, 0)),   # 9:00 PM - 10:00 PM
        ]
        for start, end in default_slots:
            TimeSlot.objects.create(start_time=start, end_time=end, is_active=True)
        available_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    # Get today's date for filtering
    from django.utils import timezone
    from datetime import datetime
    today = timezone.now().date()
    
    if request.method == 'POST':
        name = request.POST.get('user_name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('user_email')
        total_person = request.POST.get('total_person')
        booking_data = request.POST.get('booking_data')
        booking_time = request.POST.get('booking_time')

        # Debug: Print received data
        print(f"DEBUG: name={name}, phone={phone_number}, email={email}, persons={total_person}, date={booking_data}, time={booking_time}")

        # Validate form data
        if not all([name, phone_number, email, total_person, booking_data, booking_time]):
            messages.error(request, 'Please fill all fields including time slot.')
            return render(request, 'book_table.html', {
                'google_maps_api_key': google_maps_api_key,
                'available_slots': available_slots,
                'booked_slots': list(BookTable.objects.filter(
                    Booking_date__gte=today,
                    Status__in=['pending', 'confirmed']
                ).values('Booking_date', 'Booking_time'))
            })
        
        # Validate phone number
        if len(phone_number) != 10:
            messages.error(request, 'Phone number must be 10 digits.')
            return render(request, 'book_table.html', {
                'google_maps_api_key': google_maps_api_key,
                'available_slots': available_slots,
                'booked_slots': list(BookTable.objects.filter(
                    Booking_date__gte=today,
                    Status__in=['pending', 'confirmed']
                ).values('Booking_date', 'Booking_time'))
            })

        # Check if time slot is already booked
        existing_booking = BookTable.objects.filter(
            Booking_date=booking_data,
            Booking_time=booking_time,
            Status__in=['pending', 'confirmed']
        ).first()
        
        if existing_booking:
            messages.error(request, 'Sorry, this time slot is already booked. Please select another time.')
            return render(request, 'book_table.html', {
                'google_maps_api_key': google_maps_api_key,
                'available_slots': available_slots,
                'booked_slots': list(BookTable.objects.filter(
                    Booking_date=booking_data,
                    Status__in=['pending', 'confirmed']
                ).values_list('Booking_time', flat=True))
            })
        
        # Save booking data to the database
        data = BookTable(Name=name, Phone_number=phone_number,
                         Email=email, Total_person=total_person,
                         Booking_date=booking_data, Booking_time=booking_time)
        data.save()

        # Add success message
        messages.success(request, 'Booking request submitted successfully!')

        # Redirect to same page with success message
        return render(request, 'book_table.html', {
            'google_maps_api_key': google_maps_api_key,
            'available_slots': available_slots,
            'booked_slots': list(BookTable.objects.filter(
                Booking_date__gte=today,
                Status__in=['pending', 'confirmed']
            ).values('Booking_date', 'Booking_time')),
            'success': True
        })

    # Get today's booked slots for calendar display
    booked_slots = BookTable.objects.filter(
        Booking_date__gte=today,
        Status__in=['pending', 'confirmed']
    ).values('Booking_date', 'Booking_time')
    
    return render(request, 'book_table.html', {
        'google_maps_api_key': google_maps_api_key,
        'available_slots': available_slots,
        'booked_slots': list(booked_slots)
    })


@csrf_exempt
def FeedbackView(request):
    if request.method == 'POST':
        # Get data from the form
        name = request.POST.get('User_name')
        feedback = request.POST.get('Description')  # Assuming 'Feedback' field is a description
        rating = request.POST.get('Rating')
        image = request.FILES.get('Selfie')  # 'Selfie' field from the form

        # Print to check the values
        print('-->', name, feedback, rating, image)

        # Check if the name is provided
        if name != '':
            # Save the feedback data to the Feedback model
            feedback_data = Feedback(
                User_name=name,
                Description=feedback,
                Rating=rating,
                Image=image  # Save the uploaded image
            )
            feedback_data.save()

            # Add success message
            messages.success(request, 'Feedback submitted successfully!')

            # Optionally, you can redirect or return a success message
            return render(request, 'feedback.html', {'success': 'Feedback submitted successfully!'})
    
    # Handle GET request - just show the feedback form
    return render(request, 'feedback.html')

@login_required
def order_tracking(request, order_id=None):
    """Live order tracking for customers"""
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return render(request, 'order_tracking.html', {'order': order})
    else:
        # Show all active orders for the user
        active_orders = Order.objects.filter(
            user=request.user,
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).order_by('-created_at')
        return render(request, 'order_tracking.html', {'orders': active_orders})


@login_required
@user_passes_test(lambda u: u.is_staff)
def kitchen_display(request):
    """Kitchen Display System for staff"""
    # Get orders that need preparation
    pending_orders = Order.objects.filter(
        status__in=['pending', 'confirmed', 'preparing']
    ).order_by('created_at')
    
    # Get recent completed orders (last 30 minutes)
    from django.utils import timezone
    from datetime import timedelta
    completed_orders = Order.objects.filter(
        status__in=['ready', 'delivered'],
        updated_at__gte=timezone.now() - timedelta(minutes=30)
    ).order_by('-updated_at')[:10]
    
    context = {
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
    }
    return render(request, 'kitchen_display.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def update_order_status(request, order_id):
    """Update order status (for kitchen staff)"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        
        if new_status in ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled']:
            order.status = new_status
            order.save()
            
            # Send notification to customer
            subject = f'Order #{order.id} Update'
            message = f"Hello {order.user.username},\n\nYour order status has been updated to: {new_status.upper()}\n\nThank you for your patience!"
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            
            return JsonResponse({'success': True, 'status': new_status})
    
    return JsonResponse({'success': False}, status=400)


@login_required
def checkout(request):
    """Checkout page - convert cart to order"""
    cart_items = Cart.objects.filter(user=request.user).select_related('item')
    
    if not cart_items.exists():
        messages.error(request, 'Your cart is empty!')
        return redirect('Menu')
    
    # Calculate totals
    total = sum(item.item.Price * item.quantity for item in cart_items)
    
    # Get user profile
    try:
        profile = request.user.customerprofile
    except:
        profile = None
    
    if request.method == 'POST':
        # Get form data
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            delivery_address=f"{address}, {city}, {postal_code}",
            phone=phone,
            status='pending'
        )
        
        # Add items to order
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                item=cart_item.item,
                quantity=cart_item.quantity,
                price=cart_item.item.Price
            )
        
        # Clear cart
        cart_items.delete()
        
        # Add loyalty points
        from Base_App.models import LoyaltyPoints
        loyalty, _ = LoyaltyPoints.objects.get_or_create(user=request.user)
        points_earned = len(cart_items) * 10
        loyalty.points += points_earned
        loyalty.update_tier()
        
        # Send confirmation email
        subject = f'Order #{order.id} Confirmed'
        message = f"Hello {request.user.username},\n\nYour order has been placed successfully!\n\nOrder ID: #{order.id}\nTotal: ₹{total}\nStatus: Pending\n\nThank you for ordering!"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [request.user.email])
        
        messages.success(request, f'Order #{order.id} placed successfully! You earned {points_earned} loyalty points.')
        return redirect('order_tracking_detail', order_id=order.id)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'profile': profile,
    }
    return render(request, 'checkout.html', context)
