// src/tests/msw/handlers.js
import { http } from 'msw';

// Mock authentication endpoint
export const handlers = [
  http.post('/api/auth/login', async (req, res, ctx) => {
    const { email, password } = await req.json();
    if (email === 'demo@example.com' && password === 'password') {
      return res(
        ctx.status(200),
        ctx.json({ token: 'fake-jwt-token', user: { id: 'u1', name: 'Demo User' } })
      );
    }
    return res(ctx.status(401), ctx.json({ error: 'Invalid credentials' }));
  }),



  // Mock dashboard data endpoint
  http.get('/api/dashboard', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        revenue: { value: 12345.67, currency_meta: { currency_code: 'USD', currency_symbol: '$', scale: 'USD' } },
        expenses: { value: 5432.10, currency_meta: { currency_code: 'USD', currency_symbol: '$', scale: 'USD' } },
        // add other fields as needed for UI rendering
      })
    );
  }),

  // Mock upload endpoint
  http.post('/api/upload', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ jobId: 'job-123' }));
  }),

  // Mock processing status endpoint
  http.get('/api/job/:jobId/status', (req, res, ctx) => {
    const { jobId } = req.params;
    return res(
      ctx.status(200),
      ctx.json({ jobId, status: 'completed', result: { analysis: 'sample result' } })
    );
  }),

  // Mock chatbot endpoint
  http.post('/api/chatbot', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ reply: 'Chatbot response placeholder' })
    );
  }),
];
