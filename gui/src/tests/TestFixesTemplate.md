# GUI Test Fixes Template

This template can be used to fix the remaining failing tests in the GUI components.

## Common Fixes

1. Use `getAllByXXX` instead of `getByXXX` when multiple matching elements might be found

```typescript
// Instead of:
const button = screen.getByLabelText('Submit');

// Use:
const buttons = screen.getAllByLabelText('Submit');
const button = buttons[0]; // Use the first match
```

2. Replace Jest-DOM matchers with standard assertions

```typescript
// Instead of:
expect(element).toBeInTheDocument();

// Use:
expect(element).toBeTruthy();
```

```typescript
// Instead of:
expect(element).toHaveAttribute('type', 'submit');

// Use:
expect(element.getAttribute('type')).toBe('submit');
```

```typescript
// Instead of:
expect(element).toHaveTextContent('Hello');

// Use:
expect(element.textContent).toBe('Hello');
// or
expect(element.textContent).toContain('Hello');
```

```typescript
// Instead of:
expect(element).toBeDisabled();

// Use:
expect(element.disabled).toBe(true);
// or
expect(element.hasAttribute('disabled')).toBe(true);
```

```typescript
// Instead of:
expect(element).toBeChecked();

// Use:
expect(element.checked).toBe(true);
```

3. Add explicit matchMedia mock to test files

```typescript
// Add to the top of your test file
beforeAll(() => {
  // Mock matchMedia
  if (typeof window !== 'undefined') {
    window.matchMedia = vi.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  }
});
```

4. Use MantineTestProvider instead of MantineProvider

```typescript
// Instead of:
import { MantineProvider } from '@mantine/core';

// Use:
import { MantineTestProvider } from '../../../tests/MantineTestProvider';
```

```typescript
// Instead of:
<MantineProvider>
  <Component />
</MantineProvider>

// Use:
<MantineTestProvider>
  <Component />
</MantineTestProvider>
```

5. Use renderWithProviders from utils.tsx for comprehensive test wrapper

```typescript
// Instead of:
render(<Component />);

// Use:
import { renderWithProviders } from '../../../tests/utils';
renderWithProviders(<Component />);
```

## Common Error Messages and Solutions

1. "Found multiple elements with the text of: X"
   - Use `getAllByText` instead of `getByText`

2. "window.matchMedia is not a function"
   - Add matchMedia mock to test file (see above)

3. "Invalid Chai property: toBeInTheDocument"
   - Replace Jest-DOM matcher with standard assertion (see above)

4. "Element type is invalid: expected a string or a class/function"
   - Check component imports and ensure all components are properly defined

By applying these fixes to tests, you can ensure they work properly in the Jest-DOM and JSDOM environment.