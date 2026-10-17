import { demoMembers, demoTeams } from "@/lib/sample-company";

export function MemberSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <label className="reader-control">View as<select aria-label="Memory reader" value={value} onChange={(event) => onChange(event.target.value)}>
    {demoTeams.map((team) => <optgroup key={team.slug} label={`${team.label} · ${team.count} members`}>
      {demoMembers.filter((member) => member.team === team.slug).map((member) => <option key={member.path} value={member.path}>{member.label}</option>)}
    </optgroup>)}
  </select></label>;
}
