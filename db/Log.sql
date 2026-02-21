-- EventLogs Table
CREATE TABLE EventLogs (
  event_id UUID PRIMARY KEY,
  user_id UUID,
  portfolio_id UUID,
  event_type VARCHAR(100),       -- e.g., 'Login', 'TransactionEntry', 'SimulationRun'
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (portfolio_id) REFERENCES Portfolio(portfolio_id)
);