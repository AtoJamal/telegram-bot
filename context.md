Here is a complete, step-by-step plan for my project, breaking down each phase from the user's initial interaction to the final delivery of the CV.

Phase 1: The User's Journey with the Telegram Bot
This phase covers everything the user will experience directly.

1 Starting the Bot: The user finds my bot in Telegram and presses the "Start" button.

2 Viewing Templates: The bot immediately fetches and displays the first 10 CV templates from Canva. Each template is shown as an image with its own "Order This Template" button below it.

3 Navigating Templates: After the 10th template, the bot presents two buttons: "Next Page" (to see the next 10 templates) and another "Order This Template" (for the 10th template). This pattern continues for all available templates.

4 Selecting a Template: The user finds a design they like and clicks its "Order This Template" button. The bot now knows which design the user wants.

5 Collecting User Information: The bot begins a structured conversation to gather the necessary details for the CV, asking for one piece of information at a time:

"What is your full name?"

"Please provide your contact information (phone, email, etc.)."

"Describe your professional experience."

"List your skills."

...and so on for education, references, etc.

6 Confirming Information: After collecting all the details, the bot displays a complete summary of the information provided by the user. It then asks, "Is all of this information correct?" and provides two buttons: "Yes, Correct" and "No, I need to make a change."

7 Editing Information: If the user clicks "No," the bot lists each piece of information with a number (e.g., 1. Name, 2. Skills). It asks the user to type the number of the field they wish to edit. The bot then re-asks for that specific piece of information. This process repeats until the user confirms everything is correct by clicking "Yes, Correct."

8 Payment Instructions: The bot sends a message with my bank account details and the amount to be paid (100 Birr). It explicitly instructs the user to upload a screenshot of the payment confirmation.

9 Receiving Payment Proof: The user uploads the screenshot image (JPG or PNG) directly into the chat.

10 Pending Confirmation: Once the bot receives the image, it sends a final message for this stage: "Thank you. Your payment is being processed. We will notify you once it's verified. Please come back later."

Phase 2: Backend and Admin/Designer Workflow
This phase covers the behind-the-scenes processes in Django and Firebase.

11 Initial Project Setup:

I will create a new Django project.

I will set up a new Firebase project, making sure to enable both Firestore Database (to store order data) and Firebase Storage (to store images and final CVs).

I will securely store my API keys (for Telegram, Canva, and Firebase) in my Django project's configuration.

Creating the Order: When the user confirms their CV details are correct (Step 7), my Django backend creates a new "order" document in my Firestore database. This document contains the user's Telegram ID, the chosen Canva template ID, all the CV information, and an initial status like "awaiting_payment".

12 Handling the Screenshot Upload:

The Telegram bot forwards the user's uploaded screenshot to my Django application.

Django receives the image and uploads it to a specific folder in my Firebase Storage.

Firebase Storage provides a secure and permanent URL for the uploaded image.

Django then updates the order document in Firestore, adding this new payment_screenshot_url and changing the status to "pending_verification".

13 Admin Verification Process:

An administrator logs into the Django Admin Dashboard.

They navigate to an "Orders" section that lists all orders from Firestore.

They filter for orders with the "pending_verification" status.

14 Clicking on an order reveals all its details: the user's CV info, the Canva template ID, and a clickable link to the payment screenshot.

The admin clicks the link to view the screenshot and confirm the payment was made.

15 Approving the Order:

Within the Django admin, the administrator changes the order's status to "approved".

The system automatically sets a delivery date (e.g., three days from the current date).

This status change triggers the bot to send a new message to the user: "Payment confirmed! Your order is now being processed and will be delivered by {delivery_date}."

16 The Designer's Role:

A designer logs into the Django admin and views all orders with the "approved" status.

For each order, they have access to all the information they need: the user's details and the specific Canva template to use.

The designer creates the CV.

17 Uploading the Final CV:

Once the CV is finished (as a PDF), the designer returns to the order in the Django admin.

They use a file upload field to add the final CV document to the order.

The backend uploads this PDF to Firebase Storage, gets the URL, and saves it as final_cv_url in the order document.

Finally, the order's status is changed to "completed".

Phase 3: Automated Final Delivery
This final phase ensures the user gets their CV without any further manual intervention.

18 Setting Up a Scheduled Task: I will configure a "cron job" or a scheduled task on my server. This is a script that is set to run automatically at regular intervals (e.g., every hour).

19 The Delivery Script's Job: Every hour, the script will automatically:

Query my Firestore database for any orders that meet all of the following conditions:

The status is "completed".

The delivery_date is today or has already passed.

The order has not already been marked as "delivered".

20 Sending the CV:

For each order it finds, the script gets the user's Telegram ID and the final_cv_url.

It then uses the Telegram Bot API to send a final message to the user, attaching the CV file directly. The message will read: "Your CV is ready! Thank you for using our service."

After the file is sent successfully, the script updates the order's status in Firestore to "delivered" to ensure it is never sent again.
