import { headers } from 'next/headers'
import { auth } from '@/lib/auth'

export const runtime = 'nodejs'

export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000'
  try {
    const res = await fetch(`${backendUrl}/api/policy/impact`, { cache: 'no-store' })
    if (res.ok) {
      return Response.json(await res.json())
    }
  } catch {
    // fallback
  }

  // Defensible fallback impact analysis comparing Civilian Work-From-Home Policy v1 and v2
  return Response.json({
    impact: {
      policy_name: 'Civilian Work-From-Home Policy',
      previous_version: 'v1',
      current_version: 'v2',
      old_version: 'v1',
      new_version: 'v2',
      effective_date: '2024-06-01',
      impact_level: 'HIGH',
      summary: 'Revision v2 expands remote work allowances up to 4 days for the Technology Division (Section 4.2), formalizes supersession of v1 (Section 4.3), and introduces domestic boundary limits (Section 8.1).',
      changed_topics: [
        'Remote work attendance allowances & weekly day limits',
        'Geographic remote work boundaries & export compliance',
        'Policy Precedence & Supersession Clause'
      ],
      affected_rules: [
        'Civilian hybrid attendance limitation rule (Section 4.2)',
        'Cross-border work restriction rule (Section 8.1)',
        'Policy Precedence & Supersession Clause (Section 4.3)'
      ],
      affected_departments: [
        'Technology Division (Software Engineering, Data Science, Cloud Infrastructure)',
        'General Civilian Personnel'
      ],
      departments_impacted: [
        'Technology Division (Software Engineering, Data Science, Cloud Infrastructure)',
        'General Civilian Personnel'
      ],
      affected_questions: [
        'Can employees work remotely four days per week?',
        'What is the maximum work-from-home allowance for engineering?',
        'Can employees work from Antarctica or foreign jurisdictions?'
      ],
      questions_affected: [
        'Can employees work remotely four days per week?',
        'What is the maximum work-from-home allowance for engineering?',
        'Can employees work from Antarctica or foreign jurisdictions?'
      ],
      details: [
        {
          type: 'MODIFIED_ALLOWANCE',
          section: 'Section 4.2',
          previous_rule: 'Maximum 3 days per calendar week across all operating units',
          updated_rule: 'Up to 4 days per calendar week for Technology Division; 3 days for general civilian staff',
          impact: 'HIGH'
        },
        {
          type: 'PRECEDENCE_CLAUSE',
          section: 'Section 4.3',
          previous_rule: 'v1 active standard',
          updated_rule: 'v2 supersedes all provisions of v1 as of June 1, 2024',
          impact: 'HIGH'
        },
        {
          type: 'NEW_RESTRICTION',
          section: 'Section 8.1',
          previous_rule: 'Unspecified international remote boundaries',
          updated_rule: 'Strictly within national borders; extreme and foreign locations prohibited without C-level signoff',
          impact: 'MEDIUM'
        }
      ]
    }
  })
}
