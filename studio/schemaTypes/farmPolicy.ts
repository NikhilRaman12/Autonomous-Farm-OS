import {defineField, defineType} from 'sanity'

export const farmPolicy = defineType({
  name: 'farmPolicy',
  title: 'Farm Policy',
  type: 'document',
  fields: [
    defineField({name: 'title', title: 'Title', type: 'string', validation: r => r.required()}),
    defineField({name: 'objective', title: 'Objective', type: 'text', validation: r => r.required()}),
    defineField({name: 'maxWaterStress', title: 'Maximum water-stress threshold (%)', type: 'number', validation: r => r.required().min(0).max(100)}),
    defineField({name: 'minimumDemandToSell', title: 'Minimum demand to sell', type: 'number', validation: r => r.required().min(0).max(1)}),
    defineField({name: 'inventoryReservePercent', title: 'Inventory reserve (%)', type: 'number', validation: r => r.required().min(0).max(100)}),
    defineField({name: 'notes', title: 'Operational notes', type: 'text'}),
  ],
})
