import { Dropdown, DropdownItem } from "flowbite-react";

export default function Component() {
  return (
    <Dropdown label="Currently chosen" dismissOnClick={true}>
      <DropdownItem>Ascending</DropdownItem>
      <DropdownItem>Descending</DropdownItem>
    </Dropdown>
  );
}
