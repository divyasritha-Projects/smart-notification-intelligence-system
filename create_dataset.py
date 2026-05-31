import csv
import random

high_messages = [
    "Bank OTP 1234",""
    "Your OTP is 123456",
    "Use OTP 987654 for login",
    "Verification code is 445566",
    "Do not share your OTP",
    "Enter OTP to continue transaction",
    "OTP for payment is 778899"
    "Salary credited",
    "Project meeting tomorrow",
    "Client call today",
    "Urgent notice from boss",
    "Submit report by EOD",
    "Payment due today",
    "Flight booking confirmed",
    "Doctor appointment tomorrow",
    "Deadline for assignment"
]

medium_messages = [
    "Friend party invitation",
    "Team deadline reminder",
    "College exam reminder",
    "Weekly newsletter",
    "Gym session schedule",
    "Upcoming webinar info",
    "Library book due reminder",
    "Meeting rescheduled",
    "Friend's birthday party",
    "Monthly report update"
]

low_messages = [
    "Sale on electronics",
    "Discount on grocery",
    "Fun meme from friend",
    "Daily horoscope",
    "New movie released",
    "Coupon code for shopping",
    "Festival greetings",
    "Social media notification",
    "Music playlist update",
    "Newsletter about games"
]

def add_variation(msg):
    variations = [
        msg,
        msg + " now",
        "Important: " + msg,
        msg + "!!!",
        msg.replace("today", "now")
    ]
    return random.choice(variations)


samples_per_class = 100  
csv_file = 'messages_dataset.csv'

with open(csv_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Message Text', 'Priority', 'Source'])
    
    for _ in range(samples_per_class):
        high_msg = add_variation(random.choice(high_messages))
        medium_msg = add_variation(random.choice(medium_messages))
        low_msg = add_variation(random.choice(low_messages))
        
        writer.writerow([high_msg, 'High', random.choice(['SMS', 'Gmail', 'WhatsApp', 'Telegram'])])
        writer.writerow([medium_msg, 'Medium', random.choice(['SMS', 'Gmail', 'WhatsApp', 'Telegram'])])
        writer.writerow([low_msg, 'Low', random.choice(['SMS', 'Gmail', 'WhatsApp', 'Telegram'])])

print(f"Dataset '{csv_file}' created successfully with {samples_per_class*3} messages!")