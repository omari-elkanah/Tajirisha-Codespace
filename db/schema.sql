-- User Table
CREATE TABLE "Users" (
  user_id UUID PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  year_of_study INT NOT NULL
);

-- Simulation Table
CREATE TABLE "Simulation" (
  simulation_id UUID PRIMARY KEY,
  portfolio_id VARCHAR(255) NOT NULL,   -- switched from UUID to VARCHAR
  scenario_type VARCHAR(50) NOT NULL,
  risk_level INT NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  expected_return DECIMAL(6,2) NOT NULL,
  FOREIGN KEY (portfolio_id) REFERENCES "Portfolios"(portfolio_id)
);

-- CommunityPost Table
CREATE TABLE "CommunityPost" (
  post_id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  parent_post_id UUID,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES "Users"(user_id),
  FOREIGN KEY (parent_post_id) REFERENCES "CommunityPost"(post_id)
);

-- LiteracyContent Table
CREATE TABLE "LiteracyContent" (
  content_id UUID PRIMARY KEY,
  topic VARCHAR(100),
  difficulty VARCHAR(50),
  content_type VARCHAR(50) -- e.g., 'Lesson', 'Quiz'
);

-- AssessmentResult Table
CREATE TABLE "AssessmentResult" (
  assessment_id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  content_id UUID NOT NULL,
  score INT CHECK (score BETWEEN 0 AND 100),
  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES "Users"(user_id),
  FOREIGN KEY (content_id) REFERENCES "LiteracyContent"(content_id)
);

-- UserContentAccess Table
CREATE TABLE "UserContentAccess" (
  access_id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  content_id UUID NOT NULL,
  accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES "Users"(user_id),
  FOREIGN KEY (content_id) REFERENCES "LiteracyContent"(content_id)
);

-- Budget Table
CREATE TABLE "Budget" (
  budget_id UUID PRIMARY KEY,
  portfolio_id UUID NOT NULL,
  income DECIMAL(12,2),
  expense_category VARCHAR(100),
  expense_amount DECIMAL(12,2),
  FOREIGN KEY (portfolio_id) REFERENCES "Portfolios"(portfolio_id)
);

-- SavingsGoal Table
CREATE TABLE "SavingsGoal" (
  goal_id UUID PRIMARY KEY,
  portfolio_id UUID NOT NULL,
  target_amount DECIMAL(12,2),
  deadline DATE,
  category VARCHAR(100),
  progress DECIMAL(5,2),
  FOREIGN KEY (portfolio_id) REFERENCES "Portfolios"(portfolio_id)
);

-- Simulation Table
CREATE TABLE "Simulation" (
  simulation_id UUID PRIMARY KEY,
  portfolio_id UUID NOT NULL,
  scenario_type VARCHAR(100),
  risk_level INT CHECK (risk_level BETWEEN 1 AND 10),
  amount DECIMAL(12,2),
  expected_return DECIMAL(5,2),
  FOREIGN KEY (portfolio_id) REFERENCES "Portfolios"(portfolio_id)
);

-- Transaction Table
CREATE TABLE "Transaction" (
  transaction_id UUID PRIMARY KEY,
  portfolio_id UUID NOT NULL,
  type VARCHAR(50), -- e.g., 'Income', 'Expense'
  amount DECIMAL(12,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (portfolio_id) REFERENCES "Portfolios"(portfolio_id)
);

-- Nudge Table
CREATE TABLE "Nudge" (
  nudge_id UUID PRIMARY KEY,
  portfolio_id UUID NOT NULL,
  message TEXT,
  trigger_condition VARCHAR(255),
  delivered_at TIMESTAMP,
  response_status VARCHAR(50),
  FOREIGN KEY (portfolio_id) REFERENCES "Portfolios"(portfolio_id)
);

CREATE TABLE "FailedEmails" (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    reason TEXT,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);