import {defineArrayMember, defineField, defineType} from 'sanity'

export const fieldProtocol = defineType({
  name: 'fieldProtocol',
  title: 'Field Protocol',
  type: 'document',
  fields: [
    defineField({name: 'name', title: 'Protocol name', type: 'string', validation: r => r.required()}),
    defineField({name: 'action', title: 'Action', type: 'string', options: {list: ['WATER', 'PLANT', 'HARVEST', 'SELL', 'PASS']}, validation: r => r.required()}),
    defineField({name: 'preconditions', title: 'Preconditions', type: 'array', of: [defineArrayMember({type: 'string'})]}),
    defineField({name: 'safetyGuardrails', title: 'Safety guardrails', type: 'array', of: [defineArrayMember({type: 'string'})]}),
    defineField({name: 'explanation', title: 'Explanation', type: 'text', validation: r => r.required()}),
  ],
})
