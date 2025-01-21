# Self Scalable Voting System with Face Recognition

A sophisticated e-voting system with biometric authentication, developed as a university final project. The system combines advanced face recognition technology with secure voting mechanisms to ensure reliable and accurate election processes.

## 🚀 Key Features

- **Self-Scaling Architecture**
 - Application Load Balancer for traffic distribution
 - Auto Scaling Group based on CPU/Memory metrics
 - Automatic instance scaling based on voter load
 - High availability across multiple instances
 - Real-time monitoring and scaling triggers

- **Biometric Authentication**
 - Real-time face recognition using OpenCV and MediaPipe
 - Liveness detection to prevent spoofing attempts
 - Face verification for voter identity confirmation

- **Secure Voting System**
 - JWT-based authentication
 - Encrypted election data
 - Detailed audit logging
 - Vote integrity verification

- **Advanced User Management**
 - Email verification
 - Role-based access control
 - Password reset functionality
 - User profile management

- **Election Management**
 - Create and manage elections
 - Add voters with secure token generation
 - Real-time vote counting
 - Result visualization
 - Participation rate tracking

## 🛠 Technologies

### Backend
- Python Flask
- SQLAlchemy ORM
- PostgreSQL
- JWT Authentication
- Face Recognition
- OpenCV
- MediaPipe

### Frontend
- JavaScript
- HTML5/CSS3
- Tailwind CSS

### Infrastructure
- Docker
- Nginx
- AWS Services
 - Application Load Balancer (ALB)
 - Auto Scaling Group
 - ECS (Elastic Container Service)
 - ECR (Elastic Container Registry)
 - CloudWatch
 - RDS (PostgreSQL)
 - VPC

## 💻 Prerequisites

```bash
- Python 3.9+
- PostgreSQL
- Docker
- OpenCV system dependencies
```


éé
## 🔧 Installation

1. Clone the repository
```bash
git clone [repository-url]
cd voting-system
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database
```bash
flask db upgrade
```

6. Run the application
```bash
flask run
```

## 📝 Environment Variables
Please set yout env variable
```plaintext
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
SECRET_KEY=your-secret-key
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email
MAIL_PASSWORD=your-password
```

## 🔐 Security Features

- Face recognition with liveness detection
- JWT token-based authentication
- Encrypted election data
- Secure email verification
- Password hashing
- Rate limiting
- CSRF protection

## 📚 Documentation

### User Types
1. **Voter**
  - Participate in assigned elections
  - View election results
  - Update profile and face data

### Election Process
1. Election Creation
2. Voter Registration
3. Face Verification
4. Secure Voting
5. Result Calculation


## 🚀 AWS Deployment & Infrastructure
![alt text](doc/image.png)

### ECR (Elastic Container Registry)
1. Create repository
```bash
aws ecr create-repository --repository-name voting-system --region eu-central-1
```

2. Login to ECR
```bash
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin [account-id].dkr.ecr.eu-central-1.amazonaws.com
```

3. Tag and push image
```bash
docker tag voting-system:latest [account-id].dkr.ecr.eu-central-1.amazonaws.com/voting-system:latest
docker push [account-id].dkr.ecr.eu-central-1.amazonaws.com/voting-system:latest
```

### ECS (Elastic Container Service)
1. Task Definition Configuration
  - CPU: 256 (.25 vCPU)
  - Memory: 512 MB
  - Container Port: 5000
  - Host Port: 5000
  - Environment variables from SSM Parameter Store
  - Logging: CloudWatch

2. Service Configuration
  - Launch Type: FARGATE
  - Desired Tasks: 1
  - Minimum healthy percent: 100
  - Maximum percent: 200

### RDS (Relational Database Service)
- Engine: PostgreSQL 14
- Instance: db.t3.micro
- Multi-AZ: Disabled (Development)
- Storage: 20 GB GP2
- Backup Retention: 7 days

### Application Load Balancer
- Scheme: Internet-facing
- IP address type: ipv4
- Listeners:
 - HTTPS: 443 (Certificate from ACM)
 - HTTP: 80 (Redirect to HTTPS)
- Target Group:
 - Protocol: HTTP
 - Port: 5000
 - Health Check Path: /health
 - Health Check Grace Period: 60 seconds

### Auto Scaling
- Scaling policy: Target tracking
- Target value: 60% CPU utilization
- Scale-out cooldown: 60 seconds
- Scale-in cooldown: 60 seconds
- Min capacity: 1
- Max capacity: 3

### EFS (Elastic File System)
- Performance mode: General Purpose
- Used for storing voter photos
- Mount path: /static/uploads

### Security Groups
1. Load Balancer SG:
  - Inbound: 
    - HTTPS (443) from 0.0.0.0/0
    - HTTP (80) from 0.0.0.0/0
  - Outbound: All traffic

2. ECS Tasks SG:
  - Inbound: 
    - Port 5000 from Load Balancer SG
  - Outbound: All traffic

3. RDS SG:
  - Inbound: 
    - PostgreSQL (5432) from ECS Tasks SG
  - Outbound: All traffic

### Domain & SSL Configuration
1. Domain Registration:
  - Registered oylamaolustur.net through GoDaddy

2. Route 53 Configuration:
  - Created hosted zone for oylamaolustur.net
  - Updated nameservers in GoDaddy to point to Route 53
  - Created A record alias pointing to ALB

3. SSL Certificate:
  - Requested certificate through AWS Certificate Manager (ACM)
  - Validated domain ownership through Route 53
  - Attached certificate to ALB listener

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE.md file for details

## 🎓 Authors

- Alper Torun - Initial work and development

## 🙏 Acknowledgments

- University advisors and mentors
- Open source community
- Libraries and frameworks used