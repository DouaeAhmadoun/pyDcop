# BSD-3-Clause License
#
# Copyright 2017 Orange
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
from time import sleep
from unittest.mock import MagicMock

import pytest

from pydcop.infrastructure.agents import Agent
from pydcop.infrastructure.computations import Message, message_type, \
    MessagePassingComputation
from pydcop.utils.simple_repr import simple_repr
from pydcop.utils.simple_repr import from_repr


def test_message():
    msg = Message('msg_type', 'foo')
    assert msg.type == 'msg_type'
    assert msg.content == 'foo'


def test_message_serialization():
    msg = Message('msg_type')
    r = simple_repr(msg)
    obtained = from_repr(r)
    assert msg == obtained


def test_message_factory():

    MyMessage = message_type('my_msg', ['foo', 'bar'])
    msg = MyMessage(42, 21)
    assert msg.type == 'my_msg'
    assert msg.foo == 42
    assert msg.bar == 21

    with pytest.raises(ValueError):
        MyMessage(1, 2, 3)


def test_message_factory_kwargs():

    MyMessage = message_type('my_msg', ['foo', 'bar'])
    msg = MyMessage(bar=42, foo=21)
    assert msg.type == 'my_msg'
    assert msg.foo == 21
    assert msg.bar == 42

    with pytest.raises(ValueError):
        msg = MyMessage(bar=42, pouet=21)


def test_message_factory_serialization():

    MyMessage = message_type('my_msg', ['foo', 'bar'])
    msg = MyMessage(42, 21)
    r = simple_repr(msg)
    print(r)
    obtained = from_repr(r)
    assert msg == obtained


def test_setting_message_sender_on_computation():

    c = MessagePassingComputation('c')

    c.message_sender = MagicMock()

    msg = Message('type')
    c.post_msg('target', msg)

    c.message_sender.assert_called_with('c', 'target', msg, None, None)


def test_setting_message_sender_only_works_once():

    c = MessagePassingComputation('c')

    c.message_sender = MagicMock()
    with pytest.raises(AttributeError):
        c.message_sender = MagicMock()


def test_periodic_action_on_computation():

    a = Agent('a', MagicMock())
    class TestComputation(MessagePassingComputation):
        def __init__(self):
            super().__init__('test')
            self.mock = MagicMock()

        def on_start(self):
            self.add_periodic_action(0.1, self.action)

        def action(self):
            self.mock()

    c = TestComputation()

    a.add_computation(c)
    a.start()
    a.run()
    sleep(0.25)
    a.stop()

    assert c.mock.call_count == 2


def test_several_periodic_action_on_computation():

    a = Agent('a', MagicMock())
    class TestComputation(MessagePassingComputation):
        def __init__(self):
            super().__init__('test')
            self.mock1 = MagicMock()
            self.mock2 = MagicMock()

        def on_start(self):
            self.add_periodic_action(0.1, self.action1)
            self.add_periodic_action(0.2, self.action2)

        def action1(self):
            self.mock1()

        def action2(self):
            self.mock2()

    c = TestComputation()

    a.add_computation(c)
    a.start()
    a.run()
    sleep(0.25)
    a.stop()

    assert c.mock1.call_count == 2
    assert c.mock2.call_count == 1
