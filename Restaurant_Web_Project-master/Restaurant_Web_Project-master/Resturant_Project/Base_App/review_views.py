from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count
from Base_App.models import Items, ItemReview, Order, OrderItem
from django.views.decorators.http import require_POST


@login_required
@require_POST
def add_review(request, item_id):
    item = get_object_or_404(Items, id=item_id)
    rating = int(request.POST.get('rating', 0))
    review_text = request.POST.get('review_text', '')
    
    # Check if user has purchased this item
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        item=item
    ).exists()
    
    if rating < 1 or rating > 5:
        return JsonResponse({'error': 'Invalid rating'}, status=400)
    
    if not review_text.strip():
        return JsonResponse({'error': 'Review text is required'}, status=400)
    
    # Check if user already reviewed this item
    existing_review = ItemReview.objects.filter(item=item, user=request.user).first()
    
    if existing_review:
        # Update existing review
        existing_review.rating = rating
        existing_review.review_text = review_text
        existing_review.is_verified_purchase = has_purchased
        existing_review.save()
        message = 'Review updated successfully!'
    else:
        # Create new review
        review = ItemReview.objects.create(
            item=item,
            user=request.user,
            rating=rating,
            review_text=review_text,
            is_verified_purchase=has_purchased
        )
        message = 'Review added successfully!'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'rating': rating,
        'review_text': review_text,
        'is_verified_purchase': has_purchased
    })


@login_required
@require_POST
def vote_review(request, review_id):
    review = get_object_or_404(ItemReview, id=review_id)
    vote_type = request.POST.get('vote_type')
    
    if vote_type not in ['helpful', 'not_helpful']:
        return JsonResponse({'error': 'Invalid vote type'}, status=400)
    
    # Check if user already voted
    existing_vote = ReviewVote.objects.filter(review=review, user=request.user).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Remove vote if same
            existing_vote.delete()
            if vote_type == 'helpful':
                review.helpful_votes -= 1
            else:
                review.not_helpful_votes = getattr(review, 'not_helpful_votes', 0) - 1
            message = 'Vote removed'
        else:
            # Change vote
            old_type = existing_vote.vote_type
            existing_vote.vote_type = vote_type
            existing_vote.save()
            
            if old_type == 'helpful':
                review.helpful_votes -= 1
            else:
                review.not_helpful_votes = getattr(review, 'not_helpful_votes', 0) - 1
            
            if vote_type == 'helpful':
                review.helpful_votes += 1
            else:
                review.not_helpful_votes = getattr(review, 'not_helpful_votes', 0) + 1
            message = 'Vote updated'
    else:
        # Add new vote
        ReviewVote.objects.create(
            review=review,
            user=request.user,
            vote_type=vote_type
        )
        
        if vote_type == 'helpful':
            review.helpful_votes += 1
        else:
            review.not_helpful_votes = getattr(review, 'not_helpful_votes', 0) + 1
        message = 'Vote added'
    
    review.save()
    
    return JsonResponse({
        'success': True,
        'message': message,
        'helpful_votes': review.helpful_votes,
        'not_helpful_votes': getattr(review, 'not_helpful_votes', 0)
    })


def item_reviews(request, item_id):
    item = get_object_or_404(Items, id=item_id)
    reviews = ItemReview.objects.filter(item=item).order_by('-created_at')
    
    # Calculate rating statistics
    avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    rating_counts = {}
    for i in range(1, 6):
        rating_counts[i] = reviews.filter(rating=i).count()
    
    # User's review (if exists)
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
    
    context = {
        'item': item,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'total_reviews': reviews.count(),
        'rating_counts': rating_counts,
        'user_review': user_review,
    }
    
    return render(request, 'item_reviews.html', context)


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(ItemReview, id=review_id, user=request.user)
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Review deleted successfully!')
        return redirect('item_reviews', item_id=review.item.id)
    
    return render(request, 'delete_review.html', {'review': review})


def get_item_rating_info(item_id):
    """Helper function to get rating info for an item"""
    reviews = ItemReview.objects.filter(item_id=item_id)
    avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    total_reviews = reviews.count()
    
    return {
        'avg_rating': round(avg_rating, 1),
        'total_reviews': total_reviews,
        'rating_display': f"{'⭐' * int(round(avg_rating))} {round(avg_rating, 1)} ({total_reviews})"
    }
