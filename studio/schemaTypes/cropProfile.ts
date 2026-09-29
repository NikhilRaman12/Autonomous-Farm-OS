import {defineArrayMember, defineField, defineType} from 'sanity'

export const cropProfile = defineType({
  name: 'cropProfile',
  title: 'Crop Profile',
  type: 'document',
  fields: [
    defineField({name: 'name', title: 'Crop name', type: 'string', validation: r => r.required()}),
    defineField({name: 'moistureFloor', title: 'Moisture floor (%)', type: 'number', validation: r => r.required().min(0).max(100)}),
    defineField({name: 'harvestReadiness', title: 'Harvest readiness (%)', type: 'number', validation: r => r.required().min(0).max(100)}),
    defineField({name: 'expectedYieldPerPlot', title: 'Expected yield per plot', type: 'number', validation: r => r.required().min(0)}),
    defineField({name: 'marketUnit', title: 'Market unit', type: 'string', validation: r => r.required()}),
    defineField({name: 'decisionRules', title: 'Decision rules', type: 'array', of: [defineArrayMember({type: 'string'})]}),
    defineField({
      name: 'protocols',
      title: 'Operational protocols',
      type: 'array',
      of: [defineArrayMember({type: 'reference', to: [{type: 'fieldProtocol'}]})],
    }),
    defineField({
      name: 'marketRule',
      title: 'Market rule',
      type: 'reference',
      to: [{type: 'marketRule'}],
    }),
  ],
})
