import {defineArrayMember, defineField, defineType} from 'sanity'

export const marketRule = defineType({
  name: 'marketRule',
  title: 'Market Rule',
  type: 'document',
  fields: [
    defineField({name: 'name', title: 'Rule name', type: 'string', validation: r => r.required()}),
    defineField({name: 'crop', title: 'Crop', type: 'string', validation: r => r.required()}),
    defineField({name: 'minimumDemand', title: 'Minimum demand', type: 'number', validation: r => r.required().min(0).max(1)}),
    defineField({name: 'preferredTrend', title: 'Preferred trend', type: 'string', options: {list: ['rising', 'stable', 'falling']}, validation: r => r.required()}),
    defineField({name: 'rules', title: 'Rules', type: 'array', of: [defineArrayMember({type: 'string'})]}),
    defineField({name: 'rationale', title: 'Rationale', type: 'text', validation: r => r.required()}),
  ],
})
