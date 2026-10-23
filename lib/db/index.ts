import { drizzle } from 'drizzle-orm/node-postgres'
import { Pool } from 'pg'
import * as schema from './schema'

const isNeonOrProd = process.env.DATABASE_URL?.includes('neon.tech') || process.env.NODE_ENV === 'production'

export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: isNeonOrProd ? { rejectUnauthorized: false } : undefined,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
})

export const db = drizzle(pool, { schema })

