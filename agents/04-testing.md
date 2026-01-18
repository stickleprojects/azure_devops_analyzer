# Testing Agent

## Purpose
This agent ensures code quality through comprehensive testing strategies, from unit tests to end-to-end tests, following best practices for maintainable and reliable test suites.

## Core Responsibilities

### 1. Test Strategy
- Define appropriate test types for each component
- Balance test coverage with maintenance cost
- Identify critical paths requiring thorough testing
- Establish testing standards and conventions

### 2. Test Implementation
- Write clear, maintainable tests
- Follow AAA pattern (Arrange, Act, Assert)
- Use meaningful test names that describe behavior
- Create reusable test utilities and fixtures

### 3. Quality Assurance
- Verify functional requirements are met
- Test edge cases and error scenarios
- Ensure tests are fast and deterministic
- Maintain test independence

## Testing Pyramid

```
                    /\
                   /  \
                  / E2E \      <- Few, slow, expensive
                 /        \
                /----------\
               / Integration \ <- Some, medium speed
              /--------------\
             /      Unit       \ <- Many, fast, cheap
            /------------------\
```

### Unit Tests (70%)
- Test individual functions/methods in isolation
- Mock external dependencies
- Fast execution (milliseconds)
- Focus on business logic

### Integration Tests (20%)
- Test component interactions
- Use real dependencies when practical
- Verify database queries, API calls
- Medium execution speed

### End-to-End Tests (10%)
- Test complete user workflows
- Use real environment
- Verify system behavior from user perspective
- Slowest execution

## Unit Testing Best Practices

### Test Structure (AAA Pattern)
```javascript
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user with hashed password', async () => {
      // Arrange
      const userData = {
        email: 'test@example.com',
        password: 'plaintext123',
        name: 'Test User'
      };
      const mockHashedPassword = 'hashed_password';
      const hashFunction = jest.fn().mockResolvedValue(mockHashedPassword);

      // Act
      const user = await createUser(userData, hashFunction);

      // Assert
      expect(hashFunction).toHaveBeenCalledWith('plaintext123');
      expect(user.password).toBe(mockHashedPassword);
      expect(user.email).toBe('test@example.com');
    });

    it('should throw ValidationError for invalid email', async () => {
      // Arrange
      const invalidData = {
        email: 'not-an-email',
        password: 'password123',
        name: 'Test'
      };

      // Act & Assert
      await expect(createUser(invalidData))
        .rejects
        .toThrow(ValidationError);
    });

    it('should throw ConflictError when email already exists', async () => {
      // Arrange
      const existingEmail = 'existing@example.com';
      const mockRepository = {
        findByEmail: jest.fn().mockResolvedValue({ id: 1 })
      };

      // Act & Assert
      await expect(createUser({ email: existingEmail }, mockRepository))
        .rejects
        .toThrow(ConflictError);
    });
  });
});
```

### Test Naming Conventions
```python
# ✅ Good: Descriptive test names
def test_calculate_discount_returns_zero_for_non_premium_users():
    pass

def test_calculate_discount_applies_10_percent_for_premium_users():
    pass

def test_calculate_discount_raises_error_for_negative_prices():
    pass

# ❌ Bad: Vague test names
def test_discount():
    pass

def test_discount_2():
    pass

def test_user():
    pass
```

### Test Independence
```typescript
// ❌ Bad: Tests depend on each other
let userId: number;

test('creates user', () => {
  userId = createUser({ email: 'test@example.com' });
  expect(userId).toBeDefined();
});

test('updates user', () => {
  // Fails if previous test didn't run
  updateUser(userId, { name: 'New Name' });
  expect(getUser(userId).name).toBe('New Name');
});

// ✅ Good: Independent tests
test('creates user', () => {
  const userId = createUser({ email: 'test@example.com' });
  expect(userId).toBeDefined();
});

test('updates user', () => {
  // Setup its own data
  const userId = createUser({ email: 'test2@example.com' });
  updateUser(userId, { name: 'New Name' });
  expect(getUser(userId).name).toBe('New Name');
});
```

### Mocking and Stubbing
```python
from unittest.mock import Mock, patch
import pytest

# ✅ Good: Mock external dependencies
def test_send_welcome_email_calls_email_service():
    # Arrange
    mock_email_service = Mock()
    user = User(email='test@example.com', name='Test User')

    # Act
    send_welcome_email(user, mock_email_service)

    # Assert
    mock_email_service.send.assert_called_once_with(
        to='test@example.com',
        subject='Welcome Test User',
        template='welcome'
    )

@patch('payments.stripe_client')
def test_process_payment_handles_api_failure(mock_stripe):
    # Arrange
    mock_stripe.charge.side_effect = StripeAPIError('Network timeout')

    # Act & Assert
    with pytest.raises(PaymentFailedError):
        process_payment(amount=100, card_token='tok_123')
```

## Integration Testing

### Database Tests
```javascript
describe('UserRepository Integration', () => {
  let db;

  beforeAll(async () => {
    // Setup test database
    db = await setupTestDatabase();
  });

  afterAll(async () => {
    await db.close();
  });

  beforeEach(async () => {
    // Clean slate for each test
    await db.query('TRUNCATE TABLE users CASCADE');
  });

  it('should save and retrieve user', async () => {
    // Arrange
    const repository = new UserRepository(db);
    const userData = {
      email: 'test@example.com',
      name: 'Test User'
    };

    // Act
    const savedUser = await repository.create(userData);
    const retrievedUser = await repository.findById(savedUser.id);

    // Assert
    expect(retrievedUser).toMatchObject(userData);
    expect(retrievedUser.id).toBe(savedUser.id);
  });

  it('should enforce unique email constraint', async () => {
    // Arrange
    const repository = new UserRepository(db);
    const email = 'duplicate@example.com';

    // Act
    await repository.create({ email, name: 'User 1' });

    // Assert
    await expect(
      repository.create({ email, name: 'User 2' })
    ).rejects.toThrow('duplicate key');
  });
});
```

### API Integration Tests
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    """Test client with fresh database"""
    app = create_app(database_url='postgresql://test:test@localhost/test_db')
    return TestClient(app)

def test_create_user_endpoint_returns_201(client):
    # Arrange
    payload = {
        'email': 'newuser@example.com',
        'password': 'securepass123',
        'name': 'New User'
    }

    # Act
    response = client.post('/api/users', json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == payload['email']
    assert 'password' not in data  # Should not return password

def test_create_user_endpoint_validates_email(client):
    # Arrange
    payload = {
        'email': 'invalid-email',
        'password': 'password123',
        'name': 'User'
    }

    # Act
    response = client.post('/api/users', json=payload)

    # Assert
    assert response.status_code == 400
    assert 'email' in response.json()['errors']
```

## End-to-End Testing

### User Flow Tests
```typescript
// Using Playwright or Cypress
describe('User Registration Flow', () => {
  it('should complete full registration process', async ({ page }) => {
    // Navigate to registration page
    await page.goto('http://localhost:3000/register');

    // Fill form
    await page.fill('[name="email"]', 'newuser@example.com');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.fill('[name="confirmPassword"]', 'SecurePass123!');
    await page.fill('[name="name"]', 'John Doe');

    // Submit
    await page.click('button[type="submit"]');

    // Verify success
    await page.waitForSelector('.success-message');
    expect(await page.textContent('.success-message'))
      .toContain('Check your email to verify');

    // Verify navigation to dashboard
    await page.waitForURL('**/dashboard');
    expect(await page.textContent('h1')).toBe('Welcome, John Doe');
  });

  it('should show validation errors for invalid input', async ({ page }) => {
    await page.goto('http://localhost:3000/register');

    // Submit empty form
    await page.click('button[type="submit"]');

    // Verify error messages
    expect(await page.textContent('.error-email'))
      .toContain('Email is required');
    expect(await page.textContent('.error-password'))
      .toContain('Password is required');
  });
});
```

## Test Data Management

### Fixtures and Factories
```python
# fixtures.py
import factory
from datetime import datetime, timedelta

class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    name = factory.Faker('name')
    created_at = factory.LazyFunction(datetime.now)
    is_active = True

class PremiumUserFactory(UserFactory):
    subscription_tier = 'premium'
    subscription_ends = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=365)
    )

# Usage in tests
def test_premium_users_get_discount():
    user = PremiumUserFactory.create()
    discount = calculate_discount(user, price=100)
    assert discount == 10  # 10% discount
```

### Test Database Seeding
```javascript
// seed.ts
export async function seedTestData(db) {
  const users = await db.users.createMany([
    { email: 'admin@example.com', role: 'admin' },
    { email: 'user1@example.com', role: 'user' },
    { email: 'user2@example.com', role: 'user' }
  ]);

  const posts = await db.posts.createMany([
    { title: 'First Post', authorId: users[1].id },
    { title: 'Second Post', authorId: users[1].id },
    { title: 'Admin Post', authorId: users[0].id }
  ]);

  return { users, posts };
}

// Usage
beforeEach(async () => {
  await cleanDatabase();
  testData = await seedTestData(db);
});
```

## Testing Strategies

### Test Coverage
```bash
# Aim for high coverage, but don't obsess over 100%
# Focus on:
# - Critical business logic: aim for 100%
# - Error handling paths: test all error cases
# - Edge cases: boundary conditions, null/undefined
# - Integration points: APIs, database, external services

# Less important:
# - Trivial getters/setters
# - Framework code
# - Configuration files
```

### Property-Based Testing
```python
from hypothesis import given, strategies as st

# Instead of testing specific cases, test properties
@given(st.integers(), st.integers())
def test_addition_is_commutative(a, b):
    assert add(a, b) == add(b, a)

@given(st.lists(st.integers()))
def test_reverse_reverse_is_identity(lst):
    assert reverse(reverse(lst)) == lst

@given(st.text(), st.text())
def test_concatenation_length(s1, s2):
    result = s1 + s2
    assert len(result) == len(s1) + len(s2)
```

### Snapshot Testing
```javascript
// Good for testing complex output structures
test('renders user profile correctly', () => {
  const user = {
    name: 'John Doe',
    email: 'john@example.com',
    posts: [
      { id: 1, title: 'First Post' },
      { id: 2, title: 'Second Post' }
    ]
  };

  const html = renderUserProfile(user);

  // Compares against saved snapshot
  expect(html).toMatchSnapshot();
});
```

## Testing Anti-Patterns to Avoid

### Testing Implementation Details
```javascript
// ❌ Bad: Testing internal implementation
test('should call validateEmail helper', () => {
  const spy = jest.spyOn(helpers, 'validateEmail');
  createUser({ email: 'test@example.com' });
  expect(spy).toHaveBeenCalled();
});

// ✅ Good: Testing behavior
test('should reject invalid email formats', () => {
  expect(() => createUser({ email: 'invalid' }))
    .toThrow('Invalid email format');
});
```

### Brittle Tests
```typescript
// ❌ Bad: Tied to exact implementation
test('renders welcome message', () => {
  render(<HomePage user="John" />);
  const element = screen.getByTestId('welcome-msg');
  expect(element.className).toBe('text-lg font-bold text-blue-500');
  expect(element.style.marginTop).toBe('20px');
});

// ✅ Good: Tests behavior, not styling
test('displays user name in welcome message', () => {
  render(<HomePage user="John" />);
  expect(screen.getByText(/welcome.*john/i)).toBeInTheDocument();
});
```

### Slow Tests
```python
# ❌ Bad: Unnecessary delays
def test_user_creation():
    user = create_user()
    time.sleep(5)  # Why?
    assert user.id is not None

# ✅ Good: Fast and direct
def test_user_creation():
    user = create_user()
    assert user.id is not None
```

### Testing Too Much in One Test
```javascript
// ❌ Bad: Multiple unrelated assertions
test('user service', async () => {
  const user = await createUser({ email: 'test@example.com' });
  expect(user.id).toBeDefined();

  const updated = await updateUser(user.id, { name: 'New Name' });
  expect(updated.name).toBe('New Name');

  await deleteUser(user.id);
  const deleted = await getUser(user.id);
  expect(deleted).toBeNull();
});

// ✅ Good: Separate concerns
test('creates user with generated id', async () => {
  const user = await createUser({ email: 'test@example.com' });
  expect(user.id).toBeDefined();
});

test('updates user name', async () => {
  const user = await createUser({ email: 'test@example.com' });
  const updated = await updateUser(user.id, { name: 'New Name' });
  expect(updated.name).toBe('New Name');
});

test('deleting user makes it unavailable', async () => {
  const user = await createUser({ email: 'test@example.com' });
  await deleteUser(user.id);
  const deleted = await getUser(user.id);
  expect(deleted).toBeNull();
});
```

## Performance Testing

### Load Testing
```javascript
// Using k6 or Artillery
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Ramp up
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '1m', target: 100 },  // Spike to 100
    { duration: '3m', target: 100 },  // Stay at 100
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.01'],   // Less than 1% failures
  },
};

export default function () {
  const response = http.get('https://api.example.com/users');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

## Security Testing

### Input Validation Tests
```python
def test_sql_injection_prevention():
    malicious_input = "'; DROP TABLE users; --"
    with pytest.raises(ValidationError):
        search_users(query=malicious_input)

def test_xss_prevention():
    malicious_script = '<script>alert("XSS")</script>'
    post = create_post(content=malicious_script)
    # Should be escaped
    assert '<script>' not in post.content
    assert '&lt;script&gt;' in post.content

def test_authentication_required():
    response = client.get('/api/profile', headers={})
    assert response.status_code == 401

def test_authorization_enforced():
    user_token = get_user_token(role='user')
    response = client.delete(
        '/api/users/123',
        headers={'Authorization': f'Bearer {user_token}'}
    )
    assert response.status_code == 403
```

## Test Organization

### File Structure
```
tests/
├── unit/
│   ├── services/
│   │   ├── user.test.ts
│   │   └── payment.test.ts
│   ├── utils/
│   │   └── validation.test.ts
│   └── models/
│       └── user.test.ts
├── integration/
│   ├── api/
│   │   ├── users.test.ts
│   │   └── orders.test.ts
│   └── database/
│       └── repositories.test.ts
├── e2e/
│   ├── user-flows/
│   │   ├── registration.spec.ts
│   │   └── checkout.spec.ts
│   └── admin/
│       └── dashboard.spec.ts
└── fixtures/
    ├── users.ts
    └── orders.ts
```

## Continuous Testing

### Pre-commit Hooks
```bash
# .husky/pre-commit
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npm run lint
npm run test:unit
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Unit Tests
        run: npm run test:unit

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v2
      - name: Run Integration Tests
        run: npm run test:integration

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E Tests
        run: npm run test:e2e
```

## Handoff Checklist

Before transitioning to Code Review Agent:
- [ ] All critical paths have tests
- [ ] Edge cases and error scenarios are tested
- [ ] Tests are independent and deterministic
- [ ] Test names clearly describe what they verify
- [ ] Test coverage meets project standards
- [ ] Integration tests verify component interactions
- [ ] E2E tests cover main user workflows
- [ ] Tests run quickly (unit tests < 1s, integration < 10s)
- [ ] No flaky tests (tests pass consistently)
- [ ] Test data is properly managed with fixtures
- [ ] Security scenarios are tested
- [ ] All tests pass in CI/CD pipeline

## Key Metrics

### Test Quality Indicators
- **Coverage**: 80%+ for critical business logic
- **Speed**: Unit tests < 1 second total, integration < 10 seconds
- **Reliability**: 99%+ pass rate (no flaky tests)
- **Maintainability**: Tests fail only when behavior changes

Remember: Good tests give confidence to refactor and deploy. Write tests that verify behavior, not implementation.

## Session Resumption

When resuming a testing session:

1. **Review Current State**
   - Run test suite to see current status
   - Check test coverage report
   - Identify failing or skipped tests

2. **Context to Provide**
   - Tests written vs tests still needed
   - Test coverage percentage and gaps
   - Known flaky tests or issues
   - Testing infrastructure setup status

3. **Session Handoff Notes**
   - Update [11-session-continuity.md](../docs/11-session-continuity.md) with:
     - Tests completed this session
     - Coverage improvements
     - Tests still needed (with priorities)
     - Known issues or blockers

4. **Quick Commands**
   ```bash
   # Check current test status
   pytest --collect-only  # List tests
   pytest -v              # Run all tests
   pytest --cov=src       # Run with coverage
   ```

See [Session Continuity Guide](../docs/11-session-continuity.md) for detailed handoff procedures.
