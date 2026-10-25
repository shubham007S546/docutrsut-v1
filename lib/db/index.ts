import { drizzle } from 'drizzle-orm/node-postgres'
import { Pool } from 'pg'
import * as schema from './schema'

const connectionString =
  process.env.DATABASE_URL ||
  process.env.POSTGRES_URL ||
  process.env.POSTGRES_URL_NON_POOLING

const isNeonOrProd =
  connectionString?.includes('neon.tech') ||
  process.env.NODE_ENV === 'production'

export const pool = new Pool({
  connectionString: connectionString || undefined,
  ssl: isNeonOrProd ? { rejectUnauthorized: false } : undefined,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
})

export const db = drizzle(pool, { schema })


