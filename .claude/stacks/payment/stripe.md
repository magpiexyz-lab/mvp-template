---
assumes: [framework/nextjs]
packages:
  runtime: [stripe, "@stripe/stripe-js"]
  dev: []
files:
  - src/lib/stripe.ts
  - src/lib/stripe-client.ts
env:
  server: [STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET]
  client: [NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY]
ci_placeholders:
  STRIPE_SECRET_KEY: placeholder-stripe-secret
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: placeholder-stripe-publishable
  STRIPE_WEBHOOK_SECRET: placeholder-stripe-webhook-secret
clean:
  files: []
  dirs: []
gitignore: []
---
# Payment: Stripe
> Used when idea.yaml has `stack.payment: stripe`

## Packages
```bash
npm install stripe @stripe/stripe-js
```

## Files to Create

### `src/lib/stripe.ts` — Server-side Stripe client
```ts
import Stripe from "stripe";

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  // Use the latest stable Stripe API version — check https://stripe.com/docs/upgrades
  apiVersion: "2024-12-18.acacia",
});
```
- **Important:** The `apiVersion` above may be outdated. When generating this file, always check the [Stripe API changelog](https://stripe.com/docs/upgrades#api-versions) and use the latest stable version.
- Use this in API route handlers only — never import in client components

### `src/lib/stripe-client.ts` — Client-side Stripe loader
```ts
import { loadStripe } from "@stripe/stripe-js";

export const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
);
```
- Use this in client components to redirect to Stripe Checkout

## Environment Variables
```
STRIPE_SECRET_KEY=sk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## API Routes

### `src/app/api/checkout/route.ts` — Create Checkout Session
```ts
import { NextResponse } from "next/server";
import { z } from "zod";
import { stripe } from "@/lib/stripe";

const checkoutSchema = z.object({
  plan: z.string(),
  amount_cents: z.number().int().positive(),
});

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { plan, amount_cents } = checkoutSchema.parse(body);

    // TODO: Add auth check here — see auth stack file "Server-Side Auth Check" for the correct import
    // This defines `user`, whose `user.id` is referenced in metadata below
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [
        {
          price_data: {
            currency: "usd",
            product_data: { name: plan },
            unit_amount: amount_cents,
          },
          quantity: 1,
        },
      ],
      metadata: {
        user_id: user.id, // Intentional — fails build until auth is wired (see TODO above)
        plan,
        amount_cents: String(amount_cents),
      },
      success_url: `${request.headers.get("origin")}/`,
      cancel_url: `${request.headers.get("origin")}/`,
    });

    return NextResponse.json({ url: session.url });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: "Invalid request" }, { status: 400 });
    }
    return NextResponse.json({ error: "Checkout failed" }, { status: 500 });
  }
}
```

Notes:
- Validates request body with zod (plan name, price)
- Creates a Stripe Checkout Session in `payment` mode (change to `subscription` for recurring)
- Sets `success_url` and `cancel_url` back to your app
- Returns the session URL to the client
- Fire `pay_start` analytics event before redirecting — use the typed `trackPayStart()` wrapper from `events.ts` (client-side, before calling this route)
- The `user.id` reference is intentionally undefined in the template — it causes a build error until auth is integrated. See the auth stack file's "Server-Side Auth Check" section for the correct import and guard pattern. The `metadata` object is critical — the webhook handler reads `session.metadata.user_id` to update the database.

### `src/app/api/webhooks/stripe/route.ts` — Stripe Webhook Handler
```ts
import { NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { trackServerEvent } from "@/lib/analytics-server";

export async function POST(request: Request) {
  const body = await request.text();
  const signature = request.headers.get("stripe-signature");

  if (!signature) {
    return NextResponse.json({ error: "Missing signature" }, { status: 400 });
  }

  let event;
  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!
    );
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const userId = session.metadata?.user_id ?? "unknown";
    // TODO: Update user's payment status in database using userId

    await trackServerEvent("pay_success", userId, {
      plan: session.metadata?.plan ?? "",
      amount_cents: Number(session.metadata?.amount_cents ?? 0),
      provider: "stripe",
    });
  }

  return NextResponse.json({ received: true });
}
```

Notes:
- Reads the raw request body (do NOT parse JSON before verification)
- Verifies the webhook signature using `STRIPE_WEBHOOK_SECRET`
- Handles `checkout.session.completed` event: updates payment status and fires `pay_success` server-side via `trackServerEvent()` with all required EVENTS.yaml properties (`plan`, `amount_cents`, `provider`)
- Extracts `user_id`, `plan`, and `amount_cents` from session metadata (set during checkout creation)
- Returns `200` for all event types (don't error on unknown events)

## Patterns
- Use **Stripe Checkout** (hosted payment page) — never handle raw card data
- Fire `pay_start` when redirecting the user to Checkout
- Fire `pay_success` in the webhook handler (server-side confirmation)
- Always verify webhook signatures — reject requests with invalid signatures
- Use `metadata` on the Checkout Session to pass `user_id` for database updates in the webhook

## Security
- Never expose `STRIPE_SECRET_KEY` or `STRIPE_WEBHOOK_SECRET` to the client
- Always verify webhook signatures before processing events
- Use the server-side Stripe client (`stripe.ts`) only in API routes
- Validate all amounts and plan names server-side — never trust client-provided prices

## Analytics Integration
- `pay_start`: fire client-side when the client receives the Checkout URL and redirects — use the typed `trackPayStart()` wrapper from `events.ts` (per CLAUDE.md Rule 2)
- `pay_success`: fired server-side in the webhook handler via `trackServerEvent()` from `analytics-server.ts` after confirming `checkout.session.completed` — includes all required properties (`plan`, `amount_cents`, `provider`)
- See EVENTS.yaml for the full property spec for both events

## PR Instructions
- After merging, set these environment variables in your hosting provider:
  - `STRIPE_SECRET_KEY` — from Stripe Dashboard > Developers > API keys
  - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` — from Stripe Dashboard > Developers > API keys
  - `STRIPE_WEBHOOK_SECRET` — from Stripe Dashboard > Developers > Webhooks (create a webhook endpoint pointing to `https://your-domain/api/webhooks/stripe`)
- Configure the Stripe webhook to listen for `checkout.session.completed` events
